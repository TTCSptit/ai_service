from app.core.config import settings
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

_llm_cheap = None
_llm_cheap_v1 = None
_llm_cheap_v2 = None
_llm_vip = None


def get_llm_cheap():
    """Groq Llama 8B — nhanh, dùng cho routing, fact extraction, session summary."""
    global _llm_cheap
    if _llm_cheap is None:
        _llm_cheap = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name="llama-3.1-8b-instant",
            temperature=0.3,
            streaming=True
        )
    return _llm_cheap


def get_llm_cheap_v1():
    """Groq Llama 70B (Key V1) — dùng cho draft generation, tool calling."""
    global _llm_cheap_v1
    if _llm_cheap_v1 is None:
        _llm_cheap_v1 = ChatGroq(
            api_key=settings.GROQ_API_KEY_V1,
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            streaming=True
        )
    return _llm_cheap_v1


def get_llm_cheap_v2():
    """Groq Llama 70B (Key V2) — dùng cho github analysis song song với V1."""
    global _llm_cheap_v2
    if _llm_cheap_v2 is None:
        _llm_cheap_v2 = ChatGroq(
            api_key=settings.GROQ_API_KEY_V2,  
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            streaming=True
        )
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
            streaming=True
        )
    return _llm_vip
