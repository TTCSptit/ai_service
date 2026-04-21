from langchain_core.messages import HumanMessage
from langchain_community.tools import DuckDuckGoSearchRun
from app.core.llm import get_llm_cheap
from app.core.logger import logger
import asyncio

class MarketAnalyzerAgent:
    def __init__(self):
        self.search_tool = DuckDuckGoSearchRun()

    async def execute(self, message: str) -> str:
        logger.info("[Market Agent] Bắt đầu phân tích thị trường dựa trên yêu cầu...")
        try:
            extract_prompt = f"""Phân tích câu hỏi dưới đây của người dùng về định hướng nghê nghiệp/công nghệ:
"{message}"
Hỏi: Để xem xu hướng tuyển dụng, kỹ năng yêu cầu hiện tại cho vị trí này tại Việt Nam, hãy đưa ra một cụm từ tìm kiếm (search query) ngắn gọn nhất bằng tiếng Anh hoặc tiếng Việt. (ví dụ: "ReactJS requirements jobs 2025", "yêu cầu tuyển dụng Data Engineer").
CHỈ TRẢ VỀ CỤM TỪ TÌM KIẾM, KHÔNG GIẢI THÍCH."""
            
            query_response = await get_llm_cheap().ainvoke([HumanMessage(content=extract_prompt)])
            search_query = query_response.content.strip().replace('"', '')
            logger.info(f"[Market Agent] Search Query: {search_query}")
            
           
            search_results = await asyncio.to_thread(self.search_tool.run, search_query)
            
            summary_prompt = f"""Dưới đây là các kết quả từ Internet về xu hướng thị trường liên quan đến "{search_query}":
{search_results}

Hãy tóm tắt ngắn gọn thành 2-3 gạch đầu dòng những công nghệ, kỹ năng, hoặc yêu cầu nổi bật nhất mà các nhà tuyển dụng hiện nay đang tìm kiếm. Không giải thích dông dài."""
            
            summary_response = await get_llm_cheap().ainvoke([HumanMessage(content=summary_prompt)])
            market_insight = summary_response.content.strip()
            logger.info(f"[Market Agent] Kết quả phân tích: {market_insight}")
            return market_insight
            
        except Exception as e:
            logger.error(f"[Market Agent Lỗi]: {e}")
            return ""
