import asyncio
from app.core.config import settings
from langchain_groq import ChatGroq
from app.core.llm import get_llm_kaggle_v1
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

class Dummy(BaseModel):
    name: str

async def main():
    try:
        print("Đang test gọi ainvoke với structured output...")
        
        bad_groq = ChatGroq(
            api_key="gsk_invalidkey1234567890123456789012345678901234567890",
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=4000,
            streaming=True
        ).with_fallbacks([get_llm_kaggle_v1()])
        
        # This is what memory_agent.py does:
        structured_llm = bad_groq.with_structured_output(Dummy)
        
        res = await structured_llm.ainvoke([HumanMessage(content="Hello")])
        print("FALLBACK THÀNH CÔNG:", res)
    except Exception as e:
        print("ERROR:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
