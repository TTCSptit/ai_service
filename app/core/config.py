import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "AI Career Advisor Backend"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    BANA : str = os.getenv("BANA","")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY","")
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://f7d40e28.databases.neo4j.io")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "f7d40e28")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "5A6B22jjvwzpFUsAJDSiKqDdnoFLQIXc3GVCDHoNyOs")
    E2B: str = os.getenv("E2B")
    GITHUB_TOKEN :str = os.getenv("GITHUB_TOKEN")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GROQ_API_KEY_V1: str =os.getenv("GROQ_API_KEY_v1","")
    GROQ_API_KEY_V2: str = os.getenv("GROQ_API_KEY_v2","")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL","")
settings = Settings()


if not settings.GEMINI_API_KEY:
    raise ValueError("LỖI: Chưa tìm thấy GEMINI_API_KEY! Vui lòng thiết lập trong file .env hoặc thêm vào Environment Variables/Secrets trên server.")