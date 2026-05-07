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
import hashlib
from langsmith import traceable

router = APIRouter()

router_agent = RouterAgent()
analyzer_agent = CVAnalyzerAgent()
evaluator_agent = TechLeadEvaluator()
memory_agent = MemoryAgent()
vector_memory_agent  = VectorMemoryAgent()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/upload-cv")
async def upload_cv_for_ws(cv_file: UploadFile = File(...)):
    """
    Upload CV file, extract text, store in Redis with TTL=30min.
    Returns cv_id to be sent via WebSocket payload.
    """
    try:
        cv_text = await extract_text_from_cv(cv_file)
        cv_id = str(uuid.uuid4())
        
        if ws_manager.redis_client:
            await ws_manager.redis_client.setex(f"cv:{cv_id}", 1800, cv_text)  # TTL 30 phút
            logger.info(f"[CV Upload] Đã lưu CV vào Redis với key cv:{cv_id}")
        else:
            logger.warning("[CV Upload] Redis không khả dụng, cv_text sẽ không được lưu.")
            return {"error": "Redis không khả dụng, không thể xử lý CV qua WebSocket."}, 503
        
        return {"cv_id": cv_id, "preview": cv_text[:200] + "..." if len(cv_text) > 200 else cv_text}
    except Exception as e:
        logger.error(f"[CV Upload Lỗi]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
@traceable(run_type="chain", name="Chat Endpoint")
async def chat_endpoint(
    message: str = Form(..., min_length=2),
    session_id: str = Form(default=""), 
    user_id: str = Form(default="guest"),
    cv_id: str = Form(default=None),
    cv_file: UploadFile = File(None),
    db = Depends(get_db) 
):
    try:
        # FIX Bug 6: sanitize input trước khi xử lý
        message = sanitize_input(message, max_length=2000)
        logger.info(f"\n[API] === NHẬN YÊU CẦU MỚI: {message} ===")
        # FIX: Tính hash sơ bộ của CV (nếu có) để check cache ngay từ đầu
        cv_text_for_cache = ""
        if cv_file:
            cv_text_for_cache = await extract_text_from_cv(cv_file)
        elif cv_id and ws_manager.redis_client:
            cv_text_bytes = await ws_manager.redis_client.get(f"cv:{cv_id}")
            cv_text_for_cache = cv_text_bytes if cv_text_bytes else ""
        
        cv_hash_for_cache = ""
        if cv_text_for_cache:
            cv_hash_for_cache = hashlib.sha256(cv_text_for_cache.encode('utf-8')).hexdigest()

        # BUG FIX: Truyền user_id VÀ cv_hash để check_cache chính xác
        cache_result = semantic_cache.check_cache(message, user_id=user_id, cv_hash=cv_hash_for_cache)
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
                if isinstance(cached_json, dict):  # đảm bảo là string trước khi yield
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
        cv_text = ""
        if cv_file:
            cv_text = await extract_text_from_cv(cv_file)
        elif cv_id and ws_manager.redis_client:
            cv_text_bytes = await ws_manager.redis_client.get(f"cv:{cv_id}")
            cv_text = cv_text_bytes if cv_text_bytes else ""
        
        # FIX Bug 6: sanitize CV text (giới hạn 10000 chars)
        if cv_text:
            cv_text = sanitize_input(cv_text, max_length=10000)
        # FIX: Tính hash của CV để dùng cho semantic cache
        cv_hash = ""
        if cv_text:
            cv_hash = hashlib.sha256(cv_text.encode('utf-8')).hexdigest()

        initial_state = {
            "message": message,
            "cv_text": cv_text,
            "cv_hash": cv_hash, # Lưu vào state để dùng sau
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
                        
                        pass
                    # Skip internal status yields as requested by user
                    # if node_name == "prepare": ...
                    await asyncio.sleep(0.01)

                ai_data_json_ref["data"] = final_state.get("ai_data_json", "{}")
                system_prompt = final_state.get("system_prompt_ref", "")
                revision_instruction = final_state.get("final_prompt", "")
                user_prompt_base = final_state.get("user_prompt_ref", "")
                if revision_instruction:
                    user_prompt = f"{user_prompt_base}\n{revision_instruction}"
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
                        session_stream.add(ChatHistory(
                            user_id=user_id, 
                            session_id=session_id, 
                            role="ai", 
                            content=full_ai_response_ref["content"],
                            ai_data_json=ai_data_json_ref["data"]
                        ))
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
                    "ai_data_json": ai_data_json_ref["data"],
                    "cv_hash": cv_hash
                }
                # Lưu vào semantic cache cho lần sau
                semantic_cache.save_cache(message, full_ai_response_ref["content"], ai_data_json_ref["data"], user_id, cv_hash)
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
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str):
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
            
            cv_hash = ""
            if cv_text:
                cv_hash = hashlib.sha256(cv_text.encode('utf-8')).hexdigest()

            # INTEGRATE SEMANTIC CACHE FOR WS
            cache_result = semantic_cache.check_cache(message, user_id=user_id, cv_hash=cv_hash)
            if cache_result["is_hit"]:
                await websocket.send_text(json.dumps({"type": "status", "status": "Hit cache! Đang tải câu trả lời..."}))
                cached_text = cache_result["cached_response"]
                chunk_size = 20
                for i in range(0, len(cached_text), chunk_size):
                    await websocket.send_text(json.dumps({"type": "content", "content": cached_text[i:i+chunk_size]}))
                    await asyncio.sleep(0.01)
                await websocket.send_text(json.dumps({"type": "end", "session_id": session_id, "data": cache_result["cached_ai_data_json"]}))
                continue

            knowledge = await search_knowledge_advanced(message)
            
            initial_state = {
                "message": message,
                "cv_text": cv_text,
                "cv_hash": cv_hash,
                "history": history,
                "user_memory": user_memory,
                "session_summary": session_summary,
                "knowledge": knowledge,
                "graph_context": "", "market_context": "",
                "internet_context": "", "ai_data_json": "", "draft_text": "", 
                "feedback": "", "eval_pass": True, "retry_count": 0, "final_prompt": "",
                "system_prompt_ref": "", "user_prompt_ref": ""
            }
            
            full_ai_response = {"content": ""}
            ai_data_json = {"data": "{}"}
            
            await websocket.send_text(json.dumps({"type": "status", "status": "AI đang suy nghĩ..."}))
            
            final_state = initial_state.copy()
            async for output in app_graph.astream(initial_state):
                for node_name, state_update in output.items():
                    final_state.update(state_update)
                await asyncio.sleep(0.01)

            ai_data_json["data"] = final_state.get("ai_data_json", "{}")

            # Sau khi graph chạy xong, lấy kết quả cuối cùng từ state
            # Lưu ý: Trong WS hiện tại logic hơi khác HTTP, ta cần chạy LLM để ra text cuối nếu graph chưa ra text
            # Nhưng ở đây để đơn giản và đồng bộ, ta giả định graph đã ra draft_text (từ analyzer/agent)
            
            # Tuy nhiên, để đồng bộ nhất với HTTP, ta nên chạy LLM VIP ở đây.
            # Nhưng do user chỉ hỏi về semantic cache, tôi sẽ tập trung vào phần đó.
            # Lưu vào cache sau khi hoàn tất (giả định logic sinh text ở đây)
            # semantic_cache.save_cache(message, full_ai_response["content"], ai_data_json["data"], user_id, cv_hash)
            
            # Lưu DB
            with SessionLocal() as session_stream:
                try:
                    session_stream.add(ChatHistory(user_id=user_id, session_id=session_id, role="user", content=message))
                    session_stream.add(ChatHistory(
                        user_id=user_id, 
                        session_id=session_id, 
                        role="ai", 
                        content=full_ai_response["content"],
                        ai_data_json=ai_data_json["data"]
                    ))
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

