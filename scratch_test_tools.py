import asyncio
from app.core.llm import get_llm_kaggle_v1
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

@tool
def dummy_tool(x: int):
    """Dummy tool"""
    return x

async def main():
    try:
        print("Testing bind_tools with Kaggle...")
        llm = get_llm_kaggle_v1().bind_tools([dummy_tool])
        res = await llm.ainvoke([HumanMessage(content="Hello")])
        print("SUCCESS:", res)
    except Exception as e:
        print("ERROR:", str(e))

if __name__ == "__main__":
    asyncio.run(main())
