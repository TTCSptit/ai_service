from app.core.config import settings
from langchain_openai import ChatOpenAI

_llm_cheap = None
_llm_vip = None

def get_llm_cheap():
    global _llm_cheap
    if _llm_cheap is None:
        from langchain_groq import ChatGroq
        _llm_cheap = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.7,
            streaming=True
        )
    return _llm_cheap
def get_llm_vip():
    global _llm_vip
    if _llm_vip is None:
        _llm_vip = ChatOpenAI(
            api_key=settings.GITHUB_TOKEN, 
            base_url="https://models.inference.ai.azure.com", 
            model_name="gpt-4o-mini", 
            temperature=0.7,
            streaming=True
        )
    return _llm_vip
# def get_llm_vip():
#     global _llm_vip
#     if _llm_vip is None:
#         from langchain_groq import ChatGroq
#         _llm_vip = ChatGroq(
#             api_key=settings.GROQ_API_KEY,
#             model_name="llama-3.3-70b-versatile",
#             temperature=0.7,
#             streaming=True
#         )
#     return _llm_vip
# def get_llm_vip():
#     global _llm_vip
#     if _llm_vip is None:
#         from langchain_google_genai import ChatGoogleGenerativeAI
#         _llm_vip = ChatGoogleGenerativeAI(
#             api_key=settings.GEMINI_API_KEY,
#             model="gemini-3.1-pro-preview",
#             temperature=0,
#             streaming=True
#         )
#     return _llm_vip
