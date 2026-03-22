import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "AI Career Advisor Backend"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    BANA : str = os.getenv("BANA","")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY","")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD")
    E2B: str = os.getenv("E2B")
    GITHUB_TOKEN :str = os.getenv("GITHUB_TOKEN")
settings = Settings()

if not settings.GEMINI_API_KEY:
    raise ValueError("LỖI: Chưa tìm thấy GEMINI_API_KEY! Vui lòng thiết lập trong file .env hoặc thêm vào Environment Variables/Secrets trên server.")