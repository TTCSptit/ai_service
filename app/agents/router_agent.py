from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langchain_community.tools import DuckDuckGoSearchRun
from app.core.llm import get_llm_cheap
from app.prompts.system_prompts import get_router_prompt
from app.core.logger import logger

class RouterDecision(BaseModel):
    needs_internet: bool
    needs_graph: bool
    needs_cv: bool
    search_query: str

class RouterAgent:
    def __init__(self):
        self.search_tool = DuckDuckGoSearchRun()
    
    async def execute(self, message: str) -> dict:
        prompt = get_router_prompt(message)
        default_decision = {"needs_internet": False, "needs_graph": True, "needs_cv": True, "search_query": "", "internet_context": ""}
        try:
            structured_llm = get_llm_cheap().with_structured_output(RouterDecision)
            decision: RouterDecision = await structured_llm.ainvoke([HumanMessage(content=prompt)])
            
            result = decision.model_dump()
            result["internet_context"] = ""
            if result.get("needs_internet") and result.get("search_query"):
                logger.info(f"[Router Agent] Đang cào mạng cho từ khóa: {result['search_query']}")
                result["internet_context"] = self.search_tool.run(result["search_query"])
            return result
        except Exception as e:
            logger.error(f"[Router Agent Lỗi]: {e}")
            return default_decision