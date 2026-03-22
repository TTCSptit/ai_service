from langchain_core.messages import HumanMessage
from app.core.llm import get_llm_cheap
from app.prompts.system_prompts import get_memory_prompt,old_memmory_prompt
from app.core.database import SessionLocal, UserMemory,SessionSummary
from app.core.logger import logger
from typing import List
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.core.llm import get_llm_cheap
class FactList(BaseModel):
    facts: List[str]=Field(
        description="Danh sách các sự thật cụ thể về ứng viên (Kinh nghiệm, kỹ năng, mong muốn, dự án, điểm yếu...). Trả về danh sách rỗng [] nếu câu chat chỉ là chào hỏi xã giao hoặc không có thông tin mới."
    )
class VectorMemoryAgent:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        self.vector_db = Chroma(
            collection_name="user_long_term_memory",
            embedding_function=self.embeddings,
            persist_directory="./chroma_memory_db"
        )
    async def extract_and_store_facts(self,user_id:str,latest_chat:str):
        logger.info(f"[Vector Memory] Đang lọc sự thật từ tin nhắn của {user_id}...")
        prompt = f"""Phân tích đoạn chat sau và trích xuất các "Sự thật" (Facts) cốt lõi về người dùng.
            Đoạn chat: {latest_chat}
            Yêu cầu: Viết các sự thật dưới góc nhìn ngôi thứ ba (Ví dụ: "Ứng viên có 3 năm kinh nghiệm ReactJS", "Ứng viên muốn mức lương 2000$"). Chỉ lấy thông tin mới có giá trị."""
        try:
            structured_llm = get_llm_cheap().with_structured_output(FactList)
            result: FactList = await structured_llm.ainvoke([HumanMessage(content=prompt)])
            if result.facts:
                metadatas = [{"user_id": user_id} for _ in result.facts]
                self.vector_db.add_texts(texts=result.facts,metadatas=metadatas)
                logger.info(f"[Vector Memory] Đã lưu {len(result.facts)} mảnh ký ức mới vào VectorDB: {result.facts}")
            else:
                logger.info(f"[Vector Memory] Không có thông tin mới để lưu.")
        except Exception as e:
            logger.error(f"[Vector Memory Lỗi]: {e}", exc_info=True)
    def get_relevant_memory(self,user_id:str,current_message:str,k:int =3)->str:
        results = self.vector_db.similarity_search(
            query=current_message,
            k=k,
            filter={"user_id":user_id}
        )
        if not results:
            return ""
        memory_texts = [doc.page_content for doc in results]
        return "\n".join(f"- {text}" for text in memory_texts)

class MemoryAgent:
    def get_memory(self, user_id: str,db) -> str:
        record = db.query(UserMemory).filter(UserMemory.user_id==user_id).first()
        if record:
            return record.long_term_memory
        return "Chưa có thông tin gì về ứng viên này. Hãy làm quen từ đầu."
    async def update_memory_task(self, user_id: str, old_memory: str, latest_chat: str):
        logger.info(f"[Memory Agent] Đang phân tích phiên chat để cập nhật hồ sơ cho {user_id}...")
        prompt = get_memory_prompt(old_memory, latest_chat)
        try:
            response = await get_llm_cheap().ainvoke([HumanMessage(content=prompt)])
            new_memory = response.content.strip()
            db_bg = SessionLocal()
            try:
                record = db_bg.query(UserMemory).filter(UserMemory.user_id==user_id).first()
                if record:
                    record.long_term_memory = new_memory
                else:
                    new_record = UserMemory(user_id=user_id,long_term_memory=new_memory)
                    db_bg.add(new_record)
                
                db_bg.commit()
                logger.info(f"[Memory Agent] Đã lưu KÝ ỨC THỰC TẾ vào PostgreSQL cho {user_id}!")
            finally:
                db_bg.close() 
        except Exception as e:
            logger.error(f" [Memory Agent Lỗi]: {e}")
    def get_session_summary(self,session_id:str,db)->str:
        record = db.query(SessionSummary).filter(SessionSummary.session_id == session_id).first()
        if record:
            return record.summary_text
        return ""
    async def update_session_summary_task(self,session_id:str, old_summary:str,latest_chat:str):
        print(f"[Thư ký Session] Đang nén ý chính cho phiên chat {session_id}...")
        prompt= old_memmory_prompt(old_summary,latest_chat)
        try:
            response = await get_llm_cheap().ainvoke([HumanMessage(content=prompt)])
            new_summary = response.content.strip()

            db_bg =SessionLocal()
            try:
                record = db_bg.query(SessionSummary).filter(SessionSummary.session_id==session_id).first()
                if record:
                    record.summary_text = new_summary
                else:
                    new_record = SessionSummary(session_id=session_id,summary_text=new_summary)
                    db_bg.add(new_record)
                db_bg.commit()
                logger.info(f"[Thư ký Session] Đã cập nhật xong biên bản: {new_summary}")
            finally:
                db_bg.close()
        except Exception as e:
           logger.error(f"[Thư ký Session Lỗi]: {e}")