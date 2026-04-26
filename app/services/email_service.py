import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.core.logger import logger
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "").strip('"').strip("'")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip('"').strip("'")

class EmailSender:
    @staticmethod
    def send_job_notification(user_email: str, job_content_html: str):
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            logger.warning("[EmailService] Chưa cấu hình SMTP_EMAIL hoặc SMTP_PASSWORD. Bỏ qua việc gửi email.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_EMAIL
            msg['To'] = user_email
            msg['Subject'] = "[AI Career Service] Tin Tuyển Dụng Phù Hợp Với CV Của Bạn"

            # Đính kèm nội dung HTML
            msg.attach(MIMEText(job_content_html, 'html'))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()

            logger.info(f"[EmailService] Đã gửi thông báo việc làm thành công tới {user_email}")
            return True
        except Exception as e:
            logger.error(f"[EmailService Lỗi]: {e}", exc_info=True)
            return False

email_sender = EmailSender()
