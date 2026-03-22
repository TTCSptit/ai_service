import uuid
import asyncio
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends, Path
from fastapi.responses import StreamingResponse

from app.core.llm import get_llm_vip
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.core.database import SessionLocal, ChatHistory 
from app.services.rag_engine import search_knowledge_advanced
from app.services.cv_parser import extract_text_from_cv

from app.prompts.system_prompts import get_hr_advisor_prompt, get_final_revision_prompt
from app.agents.router_agent import RouterAgent
from app.agents.analyzer_agent import CVAnalyzerAgent
from app.agents.evaluator_agent import TechLeadEvaluator
from app.agents.memory_agent import MemoryAgent,VectorMemoryAgent
from starlette.background import BackgroundTasks
from app.core.logger import logger
from app.agents.graph_workflow import app_graph

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

@router.post("/chat")
async def chat_endpoint(
    message: str = Form(..., min_length=2),
    session_id: str = Form(default=""), 
    user_id: str = Form(default="guest"),
    cv_file: UploadFile = File(None),
    db = Depends(get_db) 
):
    try:
        if not session_id:
            session_id = str(uuid.uuid4())
            
        db_messages = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).order_by(ChatHistory.created_at.asc()).limit(6).all()
        history = [HumanMessage(content=m.content) if m.role == 'user' else AIMessage(content=m.content) for m in db_messages]

        user_memory = memory_agent.get_memory(user_id,db)
        user_memory += vector_memory_agent.get_relevant_memory(user_id, message)
        session_summary = memory_agent.get_session_summary(session_id,db)
        knowledge = await search_knowledge_advanced(message)
        cv_text = await extract_text_from_cv(cv_file) if cv_file else ""
        initial_state = {
            "message": message,
            "cv_text": cv_text,
            "history": history,
            "user_memory": user_memory,
            "session_summary": session_summary,
            "knowledge": knowledge,
            "internet_context": "", "ai_data_json": "", "draft_text": "", 
            "feedback": "", "eval_pass": True, "retry_count": 0, "final_prompt": "",
            "system_prompt_ref": "", "user_prompt_ref": ""
        }
        logger.info("[API] Bàn giao toàn bộ logic cho LangGraph xử lý...")
        
        final_state = await app_graph.ainvoke(initial_state)

       
        ai_data_json = final_state["ai_data_json"]
        system_prompt = final_state["system_prompt_ref"]
        revision_instruction = final_state["final_prompt"]
        user_prompt = final_state["user_prompt_ref"] + revision_instruction
        
        final_messages = [SystemMessage(content=system_prompt)] + history + [HumanMessage(content=user_prompt)]

        
        full_ai_response_ref = {"content": ""}
        async def generate_response():
            try:
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
                yield f"data: {ai_data_json}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as stream_err:
                logger.error(f"Lỗi khi Stream LLM: {stream_err}")
                error_msg = f"Lỗi Stream phát sinh từ Backend: {stream_err}".replace("\n", "\\n")
                full_ai_response_ref["content"] += "\n(Bị lỗi)"
                yield f"data: {error_msg}\n\n"
                yield "data: ---DATA---\n\n"
                yield f"data: {ai_data_json}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                session_stream = SessionLocal()
                try:
                    session_stream.add(ChatHistory(user_id=user_id, session_id=session_id, role="user", content=user_prompt))
                    session_stream.add(ChatHistory(user_id=user_id, session_id=session_id, role="ai", content=full_ai_response_ref["content"]))
                    session_stream.commit()
                except Exception as db_err:
                    logger.error(f"Lỗi lưu DB cuối luồng STREAM: {db_err}")
                finally:
                    session_stream.close()

        bg_tasks = BackgroundTasks()
        async def run_bg_tasks():
            latest_chat_str = f"User: {message}\nAI: {full_ai_response_ref['content']}"
            await memory_agent.update_memory_task(user_id, user_memory, latest_chat_str)
            await memory_agent.update_session_summary_task(session_id, session_summary, latest_chat_str)
            bg_tasks.add_task(vector_memory_agent.extract_and_store_facts, user_id, latest_chat_str)

        
        bg_tasks.add_task(run_bg_tasks)
        return StreamingResponse(generate_response(), media_type="text/event-stream", background=bg_tasks)

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

