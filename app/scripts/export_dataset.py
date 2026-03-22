import json
import os
from collections import defaultdict
from app.core.database import SessionLocal, ChatHistory
from app.core.logger import logger

SYSTEM_PROMPT = """Bạn là một Chuyên gia Nhân sự (HR) cấp cao kiêm Tech Lead tận tâm.
Nhiệm vụ của bạn là tư vấn CV, định hướng sự nghiệp và phỏng vấn kỹ thuật thuật toán (Live-Coding) một cách khắt khe nhưng mang tính xây dựng. 
Luôn trả lời súc tích, chuyên nghiệp và có chuyên môn sâu về IT."""

def export_to_chatml(output_file:str="dataset.jsonl"):
    db =SessionLocal()
    try:
        logger.info("Đang truy xuất lịch sử Chat từ PostgreSQL...")
        all_mesages = db.query(ChatHistory).order_by(ChatHistory.created_at.asc())

        if not all_mesages:
            logger.warning("Database trống! Chưa có lịch sử chat nào để xuất.")
            return
        sessions = defaultdict(list)
        for msg in all_mesages:
            sessions[msg.session_id].append(msg)
        
        logger.info(f"Tìm thấy {len(sessions)} phiên trò chuyện.")

        valid_conversations = 0
        with open(output_file,'w',encoding='utf-8') as f:
            for session_id,messages in sessions.items():
                if len(messages) <2:
                    continue
            chat_data = {"messages": [{"role": "system", "content": SYSTEM_PROMPT}]}

            for msg in messages:
                role = "assistant" if msg.role == "ai" else "user"
                chat_data["messages"].append({
                    "role":role,
                    "content": msg.content.strip()
                })
            f.write(json.dumps(chat_data,ensure_ascii=False)+'\n')
            valid_conversations +=1
        logger.info(f"XONG! Đã xuất thành công {valid_conversations} cuộc hội thoại ra: {output_file}")
    
    except Exception as e:
        logger.error(f"Lỗi khi xuất dữ liệu: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    output_path = os.path.join(os.getcwd(), "dataset.jsonl")
    export_to_chatml(output_path)
