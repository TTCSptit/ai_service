import mailtrap as mt
from app.core.config import settings
from app.core.logger import logger
import os
from dotenv import load_dotenv

load_dotenv()

MAILTRAP_TOKEN = os.getenv("MAILTRAP_TOKEN") or os.getenv("MAIL_TRAP_API", "").strip('"').strip("'")
# Mặc định sử dụng email test của Mailtrap nếu không cấu hình sender
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "hello@demomailtrap.co").strip('"').strip("'")

class EmailSender:
    @staticmethod
    def send_job_notification(user_email: str, job_content_html: str):
        if not MAILTRAP_TOKEN:
            logger.warning("[EmailService] Chưa cấu hình MAILTRAP_TOKEN. Bỏ qua việc gửi email.")
            return False

        try:
            logger.info(f"[EmailService] Đang gửi thông báo việc làm qua Mailtrap tới {user_email}...")
            
            client = mt.MailtrapClient(token=MAILTRAP_TOKEN)
            
            # Tạo mail object
            mail = mt.Mail(
                sender=mt.Address(email=SENDER_EMAIL, name="PTIT Job Finder AI"),
                to=[mt.Address(email=user_email)],
                subject="[AI Career Service] Tin Tuyển Dụng Phù Hợp Với CV Của Bạn",
                html=job_content_html, # Sử dụng html cho nội dung giàu định dạng
                category="Job Notification",
            )

            response = client.send(mail)
            
            if response.get("success"):
                logger.info(f"[EmailService] Đã gửi thông báo thành công tới {user_email} (Mailtrap)")
                return True
            else:
                logger.error(f"[EmailService Lỗi] Mailtrap phản hồi thất bại: {response}")
                return False

        except Exception as e:
            logger.error(f"[EmailService Lỗi] Không thể gửi email qua Mailtrap: {e}", exc_info=True)
            return False

email_sender = EmailSender()
