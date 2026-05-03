from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_community.tools import DuckDuckGoSearchRun
from app.core.llm import get_llm_cheap
from app.prompts.system_prompts import get_router_prompt
from app.core.logger import logger

class RouterDecision(BaseModel):
    reasoning: str = Field(description="Suy luận logic để quyết định chọn nguồn dữ liệu nào. Giải thích tại sao lại bật/tắt các cờ (needs_internet, needs_graph...).")
    response_length: str = Field(
        default="medium",
        description="'short' (1-3 câu, cho greeting/chitchat), 'medium' (200-400 từ, cho câu hỏi thông thường), 'long' (500+ từ, cho review CV đầy đủ hoặc giải thích sâu)."
    )
    is_valid_topic: bool = Field(description="True nếu câu hỏi liên quan đến IT, lập trình, công việc, phỏng vấn, sự nghiệp, học tập, đánh giá CV. False nếu là chitchat, đùa cợt, hỏi thăm cá nhân ngoài lề.")
    needs_internet: bool
    needs_graph: bool
    needs_cv: bool
    needs_market_data: bool = Field(default=False, description="True nếu cần dữ liệu tuyển dụng và yêu cầu kỹ năng thực tế trên thị trường.")
    search_query: str

class RouterAgent:
    def __init__(self):
        self.search_tool = DuckDuckGoSearchRun()
    
    async def execute(self, message: str) -> dict:
        prompt = get_router_prompt(message)
        default_decision = {"is_valid_topic": True, "needs_internet": False, "needs_graph": True, "needs_cv": True, "needs_market_data": False, "search_query": "", "internet_context": ""}
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