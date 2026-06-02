from app.core.config import settings
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

_llm_cheap = None
_llm_cheap_v1 = None
_llm_cheap_v2 = None
_llm_vip = None
_llm_kaggle_v1 = None
_llm_kaggle_v2 = None



def get_llm_cheap():
    """Groq Llama 8B — nhanh, dùng cho routing, fact extraction, session summary."""
    global _llm_cheap
    if _llm_cheap is None:
        _llm_cheap = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=4000,
            streaming=True
        ).with_fallbacks([get_llm_kaggle_v1(), get_llm_kaggle_v2()])
    return _llm_cheap


_llm_structured = None

def get_llm_structured():
    """Groq Llama 70B, streaming=False — dùng cho structured output / tool calling (FactList, SkillUpdate).
    Groq KHÔNG hỗ trợ streaming=True khi dùng with_structured_output."""
    global _llm_structured
    if _llm_structured is None:
        _llm_structured = ChatGroq(
            api_key=settings.GROQ_API_KEY_V1,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=4000,
            streaming=False  # PHẢI là False khi dùng with_structured_output
        ).with_fallbacks([get_llm_kaggle_v1(), get_llm_kaggle_v2()])
    return _llm_structured


def get_llm_cheap_v1():
    """Groq Llama 70B (Key V1) — dùng cho draft generation, tool calling."""
    global _llm_cheap_v1
    if _llm_cheap_v1 is None:
        _llm_cheap_v1 = ChatGroq(
            api_key=settings.GROQ_API_KEY_V1,
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=4000,
            streaming=True
        ).with_fallbacks([get_llm_kaggle_v1(), get_llm_kaggle_v2()])
    return _llm_cheap_v1


def get_llm_cheap_v2():
    """Groq Llama 70B (Key V2) — dùng cho github analysis song song với V1."""
    global _llm_cheap_v2
    if _llm_cheap_v2 is None:
        _llm_cheap_v2 = ChatGroq(
            api_key=settings.GROQ_API_KEY_V2,  
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=4000,
            streaming=True
        ).with_fallbacks([get_llm_kaggle_v1(), get_llm_kaggle_v2()])
    return _llm_cheap_v2


def get_llm_vip():
    """GPT-4o-mini — dùng cho evaluation và final streaming response."""
    global _llm_vip
    if _llm_vip is None:
        _llm_vip = ChatOpenAI(
            api_key=settings.GITHUB_TOKEN,
            base_url="https://models.inference.ai.azure.com",
            model_name="gpt-4o-mini",
            temperature=0.3,
            max_tokens=4000,
            streaming=False # Đổi thành False để tránh lỗi Pydantic Serialization khi dùng structured output
        ).with_fallbacks([get_llm_kaggle_v1(), get_llm_kaggle_v2()])
    return _llm_vip


def get_llm_kaggle_v1():
    """Kaggle Llama 3 via Ngrok (Backup 1)."""
    global _llm_kaggle_v1
    if _llm_kaggle_v1 is None:
        _llm_kaggle_v1 = ChatOpenAI(
            base_url=settings.KAGGLE_BACKUP_URL_1,
            api_key=settings.KAGGLE_BACKUP_KEY_1,
            model_name="my-llama3",
            temperature=0.7,
            streaming=True
        )
    return _llm_kaggle_v1


def get_llm_kaggle_v2():
    """Kaggle Llama 3 via Pinggy (Backup 2)."""
    global _llm_kaggle_v2
    if _llm_kaggle_v2 is None:
        _llm_kaggle_v2 = ChatOpenAI(
            base_url=settings.KAGGLE_BACKUP_URL_2,
            api_key=settings.KAGGLE_BACKUP_KEY_2,
            model_name="my-llama3",
            temperature=0.1,
            streaming=True
        )
    return _llm_kaggle_v2

