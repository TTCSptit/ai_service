import asyncio
import json
import logging
import aio_pika
from app.core.rabbitmq import RABBITMQ_URL, QUEUE_NAME
from app.agents.memory_agent import MemoryAgent, VectorMemoryAgent
from app.services.semantic_cache import semantic_cache
from app.agents.hunter_agent import CareerHunterAgent
from app.core.redis_conf import ws_manager
from app.services.email_service import email_sender
from app.core.logger import logger

memory_agent = MemoryAgent()
vector_memory_agent = VectorMemoryAgent()
hunter_agent = CareerHunterAgent()

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

                logger.info(f"[RabbitMQ Worker] Bắt đầu xử lý background cho user: {user_id}")

                # BUG FIX: Chạy song song tất cả LLM tasks thay vì tuần tự.
                # Trước: 4 LLM calls tuần tự → ~4-6 giây mỗi lượt
                # Sau: asyncio.gather → ~1-2 giây (chờ task chậm nhất)
                await asyncio.gather(
                    # 1. Cập nhật trí nhớ dài hạn (LLM)
                    memory_agent.update_memory_task(user_id, user_memory, latest_chat_str),
                    # 2. Cập nhật tóm tắt phiên chat (LLM)
                    memory_agent.update_session_summary_task(session_id, session_summary, latest_chat_str),
                    # 3. Trích xuất và lưu sự thật vào Vector Memory (LLM)
                    vector_memory_agent.extract_and_store_facts(user_id, latest_chat_str),
                    # 4. Đánh giá và cập nhật kỹ năng (LLM)
                    memory_agent.evaluate_and_update_skills(user_id, latest_chat_str),
                )

                # 5. Lưu cache ngữ nghĩa sau khi các task LLM hoàn tất (sync, không cần gather)
                # BUG FIX: Truyền user_id để cache được scoped đúng user, tránh data leak
                await semantic_cache.save_cache(msg_text, ai_response, ai_data_json, user_id=user_id)

                logger.info(f"[RabbitMQ Worker] Hoàn tất xử lý cho user: {user_id}")
                await ws_manager.publish_user_notification(user_id, '{"action": "background_update", "status": "completed", "message": "Hồ sơ cá nhân và kỹ năng đã được cập nhật thành công!"}')
            elif task_type == "hunt_jobs_for_cv":
                user_id = payload.get("user_id", "")
                cv_text = payload.get("cv_text", "")
                ai_data_json = payload.get("ai_data_json", "{}")
                
                # Trích xuất Email ngầm (Không làm ảnh hưởng tốc độ API)
                import re
                final_email = None
                
                # 1. Thử lấy từ kết quả LLM đã phân tích sẵn
                try:
                    ai_data = json.loads(ai_data_json)
                    if isinstance(ai_data, dict) and "candidate_info" in ai_data:
                        email_candidate = ai_data["candidate_info"].get("email", "")
                        if "@" in email_candidate and ".com" in email_candidate:
                            final_email = email_candidate
                except Exception:
                    pass
                
                # 2. Nếu LLM trích xuất xịt, dùng Regex quét lại CV
                if not final_email:
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails_in_cv = re.findall(email_pattern, cv_text)
                    if emails_in_cv:
                        final_email = emails_in_cv[0]
                
                # 3. Fallback dùng user_id nếu nó là email
                if not final_email and re.match(email_pattern, user_id):
                    final_email = user_id
                
                if not final_email:
                    logger.warning("[RabbitMQ Worker] Từ chối săn việc vì không tìm thấy Email ứng viên trong CV.")
                    return

                logger.info(f"[RabbitMQ Worker] Bắt đầu tìm việc làm (CV Hunt) cho: {final_email}")
                
                # 1. Gọi Hunter Agent để săn việc và viết nội dung Email
                email_html_content = await hunter_agent.execute(cv_text)
                
                # 2. Gửi Email thông qua SMTP
                if email_html_content:
                    await asyncio.to_thread(email_sender.send_job_notification, final_email, email_html_content)
                
                logger.info(f"[RabbitMQ Worker] Đã hoàn tất luồng săn việc cho: {final_email}")
                await ws_manager.publish_user_notification(user_id, '{"action": "job_hunt", "status": "completed", "message": "Đã tìm thấy công việc phù hợp, vui lòng kiểm tra Email!"}')
            elif task_type == "evaluate_applicant":
                import httpx
                import tempfile
                import os
                from app.services.employer_service import match_cv_to_jd
                from app.services.cv_parser import extract_text_from_cv
                from app.core.config import settings

                application_id = payload.get("application_id")
                job_id = payload.get("job_id")
                cv_url = payload.get("cv_url")
                logger.info(f"[RabbitMQ Worker] Bắt đầu đánh giá AI cho Application: {application_id}, Job: {job_id}")

                # 1. Fetch Job Description
                jd_text = ""
                async with httpx.AsyncClient() as client:
                    try:
                        job_resp = await client.get(f"{settings.DOTNET_BACKEND_URL}/api/Jobs/{job_id}")
                        if job_resp.status_code == 200:
                            job_data = job_resp.json().get("data", {})
                            jd_text = f"Title: {job_data.get('title', '')}\nDescription: {job_data.get('description', '')}"
                    except Exception as e:
                        logger.error(f"[RabbitMQ Worker] Lỗi lấy JD: {e}")
                
                # 2. Download CV File
                cv_text = ""
                if cv_url:
                    async with httpx.AsyncClient() as client:
                        try:
                            # Fetch directly from the Cloudinary URL (publicly accessible)
                            logger.info(f"[RabbitMQ Worker] Đang tải CV từ: {cv_url}")
                            cv_resp = await client.get(cv_url)
                            if cv_resp.status_code == 200:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                                    tmp_file.write(cv_resp.content)
                                    tmp_file_path = tmp_file.name
                                cv_text = extract_text_from_cv(tmp_file_path)
                                os.remove(tmp_file_path)
                            else:
                                logger.error(f"[RabbitMQ Worker] Lỗi tải CV từ {cv_url}. Mã HTTP: {cv_resp.status_code}")
                        except Exception as e:
                            logger.error(f"[RabbitMQ Worker] Lỗi tải/đọc CV: {e}")
                else:
                    logger.warning(f"[RabbitMQ Worker] Application {application_id} không có cv_url.")

                # 3. Chạy AI Match CV vs JD
                if jd_text and cv_text:
                    logger.info(f"[RabbitMQ Worker] Đang gọi LLM chấm điểm cho Application {application_id}...")
                    match_result = await asyncio.to_thread(match_cv_to_jd, cv_text, jd_text)

                    # 4. Push Kết quả về .NET Backend
                    update_payload = {
                        "applicationId": application_id,
                        "aiScore": match_result.score,
                        "aiStrengths": json.dumps(match_result.strengths, ensure_ascii=False),
                        "aiWeaknesses": json.dumps(match_result.weaknesses, ensure_ascii=False),
                        "aiReasoning": match_result.reasoning
                    }
                    async with httpx.AsyncClient() as client:
                        try:
                            put_resp = await client.put(
                                f"{settings.DOTNET_BACKEND_URL}/api/Applications/update-ai-score",
                                json=update_payload
                            )
                            if put_resp.status_code == 200:
                                logger.info(f"[RabbitMQ Worker] Đã cập nhật AI Score thành công cho Application {application_id}")
                            else:
                                logger.error(f"[RabbitMQ Worker] Cập nhật AI Score thất bại: {put_resp.text}")
                        except Exception as e:
                            logger.error(f"[RabbitMQ Worker] Lỗi gọi Webhook update-ai-score: {e}")
                else:
                    logger.warning(f"[RabbitMQ Worker] Không đủ dữ liệu (Thiếu CV hoặc JD) để chấm điểm Application {application_id}.")

            else:
                logger.warning(f"[RabbitMQ Worker] Loại task không xác định: {task_type}")

        except Exception as e:
            logger.error(f"[RabbitMQ Worker Lỗi]: {e}", exc_info=True)

async def main():
    if not RABBITMQ_URL:
        logger.error("RABBITMQ_URL chưa được cấu hình. Worker dừng hoạt động.")
        return

    logger.info("[RabbitMQ Worker] Đang kết nối tới CloudAMQP và Redis...")
    await ws_manager.connect_redis()
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1) # Xử lý từng thỏi tin nhắn một

        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        logger.info(f" [RabbitMQ Worker] Đang lắng nghe trên queue: {QUEUE_NAME}")
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
