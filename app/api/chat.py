import uuid
import asyncio
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends, Path, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.core.llm import get_llm_vip
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.core.database import SessionLocal, ChatHistory, UserSkill
from app.services.rag_engine import search_knowledge_advanced
from app.services.cv_parser import extract_text_from_cv

from app.prompts.system_prompts import get_hr_advisor_prompt, get_final_revision_prompt, sanitize_input
from app.agents.router_agent import RouterAgent
from app.agents.analyzer_agent import CVAnalyzerAgent
from app.agents.evaluator_agent import TechLeadEvaluator
from app.agents.memory_agent import MemoryAgent,VectorMemoryAgent
from app.core.logger import logger
from app.agents.graph_workflow import app_graph
from app.services.semantic_cache import semantic_cache
from app.core.rabbitmq import rabbitmq
from app.core.redis_conf import ws_manager
import json
from langsmith import traceable

router = APIRouter()

router_agent = RouterAgent()
analyzer_agent = CVAnalyzerAgent()
evaluator_agent = TechLeadEvaluator()
memory_agent = MemoryAgent()
vector_memory_agent  = VectorMemoryAgent()

# Các tiến trình ngầm (cập nhật DB, RAG) đã được chuyển sang RabbitMQ Worker.


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/chat")
@traceable(run_type="chain", name="Chat Endpoint")
async def chat_endpoint(
    message: str = Form(..., min_length=2),
    session_id: str = Form(default=""), 
    user_id: str = Form(default="guest"),
    cv_file: UploadFile = File(None),
    db = Depends(get_db) 
):
    try:
        # FIX Bug 6: sanitize input trước khi xử lý
        message = sanitize_input(message, max_length=2000)
        logger.info(f"\n[API] === NHẬN YÊU CẦU MỚI: {message} ===")
        cache_result = semantic_cache.check_cache(message)
        if cache_result["is_hit"]:
            async def generate_cached_response():
                cached_text = cache_result["cached_response"]
                if cached_text:
                    chunk_size = 20
                    for i in range(0, len(cached_text), chunk_size):
                        chunk = cached_text[i:i+chunk_size].replace("\n", "\\n")
                        yield f"data: {chunk}\n\n"
                        await asyncio.sleep(0.01)
                yield "data: ---DATA---\n\n"
                
                cached_json = cache_result['cached_ai_data_json']
                if isinstance(cached_json, dict):
                    import json
                    cached_json = json.dumps(cached_json)
                    
                yield f"data: {cached_json}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(generate_cached_response(), media_type="text/event-stream")
            
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # FIX Bug 5: tăng từ 6 → 12 messages để giữ context tốt hơn
        db_messages = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).order_by(ChatHistory.created_at.asc()).limit(12).all()
        history = [HumanMessage(content=m.content) if m.role == 'user' else AIMessage(content=m.content) for m in db_messages]

        logger.info(f"[API] Bắt đầu lấy user_memory")
        user_memory = memory_agent.get_memory(user_id,db)
        logger.info(f"[API] Bắt đầu lấy vector_memory")
        user_memory += vector_memory_agent.get_relevant_memory(user_id, message)
        logger.info(f"[API] Bắt đầu lấy session_summary")
        session_summary = memory_agent.get_session_summary(session_id,db)
        logger.info(f"[API] Bắt đầu search_knowledge_advanced")
        knowledge = await search_knowledge_advanced(message)
        logger.info(f"[API] Bắt đầu extract_text_from_cv")
        cv_text = await extract_text_from_cv(cv_file) if cv_file else ""
        # FIX Bug 6: sanitize CV text (giới hạn 10000 chars)
        if cv_text:
            cv_text = sanitize_input(cv_text, max_length=10000)
        initial_state = {
            "message": message,
            "cv_text": cv_text,
            "history": history,
            "user_memory": user_memory,
            "session_summary": session_summary,
            "knowledge": knowledge,
            "graph_context": "", "market_context": "",
            "internet_context": "", "ai_data_json": "", "draft_text": "", 
            "feedback": "", "eval_pass": True, "retry_count": 0, "final_prompt": "",
            "system_prompt_ref": "", "user_prompt_ref": ""
        }
        logger.info("[API] Chuẩn bị streaming trạng thái LangGraph lên UI...")
        
        full_ai_response_ref = {"content": ""}
        ai_data_json_ref = {"data": "{}"}
        
        async def generate_response():
            user_prompt = message # Giá trị dự phòng nếu có Exception
            try:
                final_state = initial_state.copy()
                async for output in app_graph.astream(initial_state):
                    for node_name, state_update in output.items():
                        final_state.update(state_update)
                        
                        if node_name == "prepare":
                            if "Dữ liệu Thị trường thực tế" in final_state.get("user_prompt_ref", ""):
                                yield f"data: *Đang lấy dữ liệu thị trường thực tế (Market Data)...*\\n\\n\n\n"
                            yield f"data: *Hệ thống đang thu thập Context...*\\n\\n\n\n"
                        elif node_name == "draft":
                            yield f"data: *AI đang viết nháp cấu trúc...*\\n\\n\n\n"
                        elif node_name == "evaluate":
                            if state_update.get("eval_pass"):
                                yield f"data: *Tech Lead đã phê duyệt bản nháp!*\\n\\n---\\n\\n\n\n"
                            else:
                                yield f"data: *Tech Lead yêu cầu viết lại...*\\n\\n\n\n"
                        elif node_name == "revise":
                            yield f"data: *Đang sửa lại theo phản hồi...*\\n\\n\n\n"
                        await asyncio.sleep(0.01)

                ai_data_json_ref["data"] = final_state.get("ai_data_json", "{}")
                system_prompt = final_state.get("system_prompt_ref", "")
                revision_instruction = final_state.get("final_prompt", "")
                user_prompt_base = final_state.get("user_prompt_ref", "")
                if revision_instruction:
                    user_prompt = f"{user_prompt_base}\n\n[HỆ THỐNG YÊU CẦU BỔ SUNG TỪ TECH LEAD]:\n{revision_instruction}"
                else:
                    user_prompt = user_prompt_base
                
                final_messages = [SystemMessage(content=system_prompt)] + history + [HumanMessage(content=user_prompt)]
                
                # 3. Bắt đầu stream LLM VIP
                chunk_count = 0
                async for chunk in get_llm_vip().astream(final_messages):
                    chunk_count += 1
                    text_chunk = chunk.content
                    full_ai_response_ref["content"] += text_chunk

                    safe_text = text_chunk.replace("\n", "\\n")
                    yield f"data: {safe_text}\n\n"
                
                logger.info(f"Stream LLM xong, tổng số chunk={chunk_count}, ContentLength={len(full_ai_response_ref['content'])}")
                if chunk_count == 0 or len(full_ai_response_ref["content"]) == 0:
                    fallback_msg = "Xin lỗi, hệ thống AI đang gặp sự cố khi tạo câu trả lời (hoặc câu hỏi không hợp lệ). Vui lòng thử lại!"
                    full_ai_response_ref["content"] = fallback_msg
                    yield f"data: {fallback_msg}\n\n"

                yield "data: ---DATA---\n\n"
                yield f"data: {ai_data_json_ref['data']}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as stream_err:
                logger.error(f"Lỗi khi Stream LLM: {stream_err}")
                error_msg = f"Lỗi Stream phát sinh từ Backend: {stream_err}".replace("\n", "\\n")
                full_ai_response_ref["content"] += "\n(Bị lỗi)"
                yield f"data: {error_msg}\n\n"
                yield "data: ---DATA---\n\n"
                yield f"data: {ai_data_json_ref['data']}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                # Lưu lịch sử chat vào DB
                with SessionLocal() as session_stream:
                    try:
                        session_stream.add(ChatHistory(user_id=user_id, session_id=session_id, role="user", content=user_prompt))
                        session_stream.add(ChatHistory(user_id=user_id, session_id=session_id, role="ai", content=full_ai_response_ref["content"]))
                        session_stream.commit()
                    except Exception as db_err:
                        logger.error(f"Lỗi lưu DB cuối luồng STREAM: {db_err}")

                # Chuyển dữ liệu lịch sử và logic cập nhật background sang hàng đợi RabbitMQ Cloud
                latest_chat_str = f"User: {message}\nAI: {full_ai_response_ref['content']}"
                payload = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": message,
                    "user_memory": user_memory,
                    "session_summary": session_summary,
                    "latest_chat_str": latest_chat_str,
                    "ai_response": full_ai_response_ref["content"],
                    "ai_data_json": ai_data_json_ref["data"]
                }
                asyncio.create_task(rabbitmq.publish_message("update_background", payload))
                if cv_text:
                    hunt_payload = {
                        "user_id": user_id, 
                        "cv_text": cv_text,
                        "ai_data_json": ai_data_json_ref["data"]
                    }
                    asyncio.create_task(rabbitmq.publish_message("hunt_jobs_for_cv", hunt_payload))

        return StreamingResponse(generate_response(), media_type="text/event-stream")

    except Exception as e:
        logger.critical("Hệ thống sập toàn tập!", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_user_chat_history(user_id:str = Path(...),db = Depends(get_db)):
    messages = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).order_by(ChatHistory.created_at.desc()).all()

    sessions={}
    for msg in messages:
        if msg.session_id not in sessions:
            sessions[msg.session_id]={
                "session_id":msg.session_id,
                "title": msg.content[:50] + "..." if msg.role == "user" else "session",
                "created_at" :msg.created_at
            }
    return {"user_id": user_id, "sessions": list(sessions.values())}

@router.get("/skills/{user_id}")
async def get_user_skills(user_id: str = Path(...), db = Depends(get_db)):
    skills = db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
    
    if not skills:
        return {"labels": [], "data": [], "full_data": []}
        
    labels = []
    data = []
    full_data = []
    
    for skill in skills:
        labels.append(skill.skill_name)
        data.append(skill.level)
        full_data.append({
            "skill_name": skill.skill_name,
            "level": skill.level,
            "exp_point": skill.exp_point
        })
        
    return {"labels": labels, "data": data, "full_data": full_data}



@router.websocket("/ws/chat/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str, db = Depends(get_db)):
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
                continue
                
            message = payload.get("message", "")
            session_id = payload.get("session_id", "")
            cv_id = payload.get("cv_id", "")
            
            if not message or len(message) < 2:
                await websocket.send_text(json.dumps({"error": "Tin nhắn quá ngắn"}))
                continue
                
            message = sanitize_input(message, max_length=2000)
            
            cv_text = ""
            if cv_id and ws_manager.redis_client:
                cv_text = await ws_manager.redis_client.get(f"cv:{cv_id}")
                if not cv_text:
                    cv_text = ""
            
            if not session_id:
                session_id = str(uuid.uuid4())
                
            with SessionLocal() as db_session:
                db_messages = db_session.query(ChatHistory).filter(ChatHistory.session_id == session_id).order_by(ChatHistory.created_at.asc()).limit(12).all()
                history = [HumanMessage(content=m.content) if m.role == 'user' else AIMessage(content=m.content) for m in db_messages]

                user_memory = memory_agent.get_memory(user_id, db_session)
                session_summary = memory_agent.get_session_summary(session_id, db_session)
            
            user_memory += vector_memory_agent.get_relevant_memory(user_id, message)
            knowledge = await search_knowledge_advanced(message)
            
            initial_state = {
                "message": message,
                "cv_text": cv_text,
                "history": history,
                "user_memory": user_memory,
                "session_summary": session_summary,
                "knowledge": knowledge,
                "draft": "",
                "evaluation": "",
                "retry_count": 0,
                "status": "DRAFTING"
            }
            
            full_ai_response = {"content": ""}
            ai_data_json = {"data": None}
            cached_draft_text = ""
            
            await websocket.send_text(json.dumps({"status": "AI đang suy nghĩ..."}))
            
            async for output in app_graph.astream(initial_state):
                for node_name, state in output.items():
                    if node_name == "draft" or node_name == "rejection":
                        await websocket.send_text(json.dumps({"status": "Đang viết câu trả lời..."}))
                        cached_draft_text = state.get("draft_text", cached_draft_text)
                    elif node_name == "evaluate":
                        await websocket.send_text(json.dumps({"status": "Tech Lead đang chấm điểm..."}))
                    elif node_name == "revise":
                        await websocket.send_text(json.dumps({"status": "Đang sửa lại theo ý Tech Lead..."}))
                        cached_draft_text = state.get("draft_text", cached_draft_text)
                    elif node_name == "finalize":
                        final_response = cached_draft_text
                        ai_data_json["data"] = state.get("ai_data_json")
                        
                        chunk_size = 20
                        for i in range(0, len(final_response), chunk_size):
                            chunk = final_response[i:i+chunk_size]
                            await websocket.send_text(json.dumps({"chunk": chunk}))
                            await asyncio.sleep(0.01)
                            
                        full_ai_response["content"] = final_response
                        
            await websocket.send_text(json.dumps({"ai_data_json": ai_data_json["data"], "done": True, "session_id": session_id}))
            
            # Lưu DB
            with SessionLocal() as session_stream:
                try:
                    session_stream.add(ChatHistory(user_id=user_id, session_id=session_id, role="user", content=message))
                    session_stream.add(ChatHistory(user_id=user_id, session_id=session_id, role="ai", content=full_ai_response["content"]))
                    session_stream.commit()
                except Exception as db_err:
                    logger.error(f"Lỗi lưu DB cuối luồng WS: {db_err}")
            
            # Đẩy Background task
            latest_chat_str = f"User: {message}\nAI: {full_ai_response['content']}"
            payload_bg = {
                "user_id": user_id,
                "session_id": session_id,
                "user_memory": user_memory,
                "session_summary": session_summary,
                "latest_chat_str": latest_chat_str,
                "ai_response": full_ai_response["content"],
                "ai_data_json": ai_data_json["data"]
            }
            asyncio.create_task(rabbitmq.publish_message("update_background", payload_bg))
            if cv_text:
                hunt_payload = {
                    "user_id": user_id, 
                    "cv_text": cv_text,
                    "ai_data_json": ai_data_json["data"]
                }
                asyncio.create_task(rabbitmq.publish_message("hunt_jobs_for_cv", hunt_payload))

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"Lỗi Websocket: {e}")
        ws_manager.disconnect(websocket, user_id)

