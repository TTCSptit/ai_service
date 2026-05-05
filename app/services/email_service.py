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

        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = user_email
        msg['Subject'] = "[AI Career Service] Tin Tuyển Dụng Phù Hợp Với CV Của Bạn"
        msg.attach(MIMEText(job_content_html, 'html'))

        # Chiến lược 1: Thử cổng 587 (STARTTLS)
        try:
            logger.info(f"[EmailService] Đang thử gửi email qua cổng 587 tới {user_email}...")
            server = smtplib.SMTP(SMTP_SERVER, 587, timeout=10)
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            logger.info(f"[EmailService] Đã gửi thành công qua cổng 587 tới {user_email}")
            return True
        except Exception as e587:
            logger.warning(f"[EmailService] Cổng 587 thất bại: {e587}. Đang thử cổng 465 (SSL)...")
            
            # Chiến lược 2: Thử cổng 465 (SSL) - Thường ổn định hơn trong môi trường Cloud/Azure
            try:
                server = smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=10)
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                logger.info(f"[EmailService] Đã gửi thành công qua cổng 465 tới {user_email}")
                return True
            except Exception as e465:
                logger.error(f"[EmailService Lỗi] Cả 2 cổng 587 và 465 đều thất bại.")
                logger.error(f"Lỗi 587: {e587}")
                logger.error(f"Lỗi 465: {e465}")
                
                if "Network is unreachable" in str(e465) or "101" in str(e465):
                    logger.error("HƯỚNG DẪN: Lỗi này thường do Firewall của Server (ví dụ Azure/AWS) chặn các cổng SMTP ra ngoài. Vui lòng kiểm tra lại cấu hình Security Group hoặc dùng dịch vụ Relay như SendGrid/Mailgun.")
                
                return False

email_sender = EmailSender()
