import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "AI Career Advisor Backend"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    BANA : str = os.getenv("BANA","")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY","")
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://73421c7a.databases.neo4j.io")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "73421c7a")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "pKhMlffxlYXtn0o8hoCJwOh_NFP_nzBWHl07yC__gdA")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE","73421c7a")
    AURA_INSTANCEID = os.getenv("AURA_INSTANCEID","73421c7a")
    AURA_INSTANCENAME = os.getenv("AURA_INSTANCENAME","Instance01")
    E2B: str = os.getenv("E2B")
    GITHUB_TOKEN :str = os.getenv("GITHUB_TOKEN")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GROQ_API_KEY_V1: str =os.getenv("GROQ_API_KEY_v1","")
    GROQ_API_KEY_V2: str = os.getenv("GROQ_API_KEY_v2","")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL","")
    REDIS_URL: str = os.getenv("REDIS_URL", "").strip().replace('"', '').replace("'", "")
    DOTNET_BACKEND_URL: str = os.getenv("DOTNET_BACKEND_URL", "https://jobptit-api-fbevbkfre0c4h4g4.southeastasia-01.azurewebsites.net")
    
    # Kaggle Backups
    KAGGLE_BACKUP_URL_1: str = "https://tenesha-utterable-karlyn.ngrok-free.dev/v1"
    KAGGLE_BACKUP_KEY_1: str = "sk-no-key-required"
    
    KAGGLE_BACKUP_URL_2: str = "https://yesgw-35-247-131-173.run.pinggy-free.link/v1"
    KAGGLE_BACKUP_KEY_2: str = "boc_phet"

settings = Settings()


if not settings.GEMINI_API_KEY:
    raise ValueError("LỖI: Chưa tìm thấy GEMINI_API_KEY! Vui lòng thiết lập trong file .env hoặc thêm vào Environment Variables/Secrets trên server.")