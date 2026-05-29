import logging
from langchain_core.messages import HumanMessage
from app.core.llm import get_llm_structured
from app.prompts.employer_prompts import MATCH_CV_JD_PROMPT
from app.schemas.employer import MatchResponse

logger = logging.getLogger(__name__)

async def match_cv_to_jd(cv_text: str, jd_text: str) -> MatchResponse:
    """
    So khớp nội dung CV với JD và trả về kết quả cấu trúc (MatchResponse).
    """
    try:
        # Chuẩn bị prompt
        prompt = MATCH_CV_JD_PROMPT.format(cv_text=cv_text, jd_text=jd_text)
        
        # Lấy mô hình hỗ trợ structured output (Llama 70B theo cấu hình hiện tại)
        llm = get_llm_structured()
        structured_llm = llm.with_structured_output(MatchResponse)
        
        logger.info("[Employer Service] Bắt đầu gọi LLM để đánh giá CV vs JD...")
        result: MatchResponse = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        logger.info(f"[Employer Service] Đánh giá hoàn tất. Điểm số: {result.score}")
        
        return result
    except Exception as e:
        logger.error(f"[Employer Service] Lỗi khi so khớp CV và JD: {e}")
        # Trả về kết quả mặc định nếu có lỗi
        return MatchResponse(
            score=0,
            strengths=[],
            weaknesses=[],
            reasoning=f"Lỗi hệ thống khi phân tích: {str(e)}"
        )
