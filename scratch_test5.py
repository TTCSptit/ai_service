import asyncio
from app.core.llm import get_llm_kaggle_v1
from langchain_core.messages import HumanMessage

async def main():
    try:
        print("Stress testing Kaggle...")
        tasks = [get_llm_kaggle_v1().ainvoke([HumanMessage(content=f'Hello {i}')]) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                print(f"Task {i} FAILED:", str(res))
            else:
                print(f"Task {i} SUCCESS")
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == "__main__":
    asyncio.run(main())
