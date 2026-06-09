import asyncio
from app.core.config import settings
from langchain_groq import ChatGroq
from app.core.llm import get_llm_kaggle_v1
from langchain_core.messages import HumanMessage

async def main():
    try:
        # Create a massive string (approx 15000 tokens)
        giant_string = "hello world " * 15000
        print("Đang test gọi ainvoke với bad groq để test fallback với context siêu bự...")
        
        bad_groq = ChatGroq(
            api_key="gsk_invalidkey1234567890123456789012345678901234567890",
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=4000,
            streaming=True
        ).with_fallbacks([get_llm_kaggle_v1()])
        
        res = await bad_groq.ainvoke([HumanMessage(content=giant_string)])
        print("FALLBACK THÀNH CÔNG:", res.content)
    except Exception as e:
        print("ERROR:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
