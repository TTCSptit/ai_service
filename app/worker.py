import asyncio
import json
import logging
import aio_pika
from app.core.rabbitmq import RABBITMQ_URL, QUEUE_NAME
from app.agents.memory_agent import MemoryAgent, VectorMemoryAgent
from app.services.semantic_cache import semantic_cache
from app.core.logger import logger

# Khởi tạo các Agents trong Worker
memory_agent = MemoryAgent()
vector_memory_agent = VectorMemoryAgent()

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            task_type = body.get("task_type")
            payload = body.get("payload", {})

            if task_type == "update_background":
                user_id = payload.get("user_id")
                session_id = payload.get("session_id")
                msg_text = payload.get("message")
                user_memory = payload.get("user_memory")
                session_summary = payload.get("session_summary")
                latest_chat_str = payload.get("latest_chat_str")
                ai_response = payload.get("ai_response")
                ai_data_json = payload.get("ai_data_json")

                logger.info(f"🚀 [RabbitMQ Worker] Bắt đầu xử lý background cho user: {user_id}")
                
                # Chạy các task xử lý nặng nề
                # 1. Cập nhật trí nhớ dài hạn (LLM)
                await memory_agent.update_memory_task(user_id, user_memory, latest_chat_str)
                
                # 2. Cập nhật tóm tắt phiên chat (LLM)
                await memory_agent.update_session_summary_task(session_id, session_summary, latest_chat_str)
                
                # 3. Lưu cache ngữ nghĩa (Vector DB)
                semantic_cache.save_cache(msg_text, ai_response, ai_data_json)
                
                # 4. Trích xuất và lưu sự thật vào Vector Memory
                await vector_memory_agent.extract_and_store_facts(user_id, latest_chat_str)
                
                # 5. Đánh giá và cập nhật kỹ năng (LLM)
                await memory_agent.evaluate_and_update_skills(user_id, latest_chat_str)

                logger.info(f"✅ [RabbitMQ Worker] Hoàn tất xử lý cho user: {user_id}")
            else:
                logger.warning(f"⚠️ [RabbitMQ Worker] Loại task không xác định: {task_type}")

        except Exception as e:
            logger.error(f"❌ [RabbitMQ Worker Lỗi]: {e}", exc_info=True)

async def main():
    if not RABBITMQ_URL:
        logger.error("RABBITMQ_URL chưa được cấu hình. Worker dừng hoạt động.")
        return

    logger.info("📡 [RabbitMQ Worker] Đang kết nối tới CloudAMQP...")
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1) # Xử lý từng thỏi tin nhắn một

        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        logger.info(f"👷 [RabbitMQ Worker] Đang lắng nghe trên queue: {QUEUE_NAME}")
        logger.info("Nhấn CTRL+C để dừng.")

        await queue.consume(process_message)

        try:
            # Chờ đợi vô hạn
            await asyncio.Future()
        except asyncio.CancelledError:
            logger.info("Worker đang dừng...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
