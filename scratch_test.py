import asyncio
from app.core.llm import get_llm_kaggle_v1
from langchain_core.messages import HumanMessage

async def main():
    try:
        res = await get_llm_kaggle_v1().ainvoke([HumanMessage(content='Hello')])
        print(res.content)
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == "__main__":
    asyncio.run(main())
