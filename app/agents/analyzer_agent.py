from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.core.llm import get_llm_cheap
from app.prompts.system_prompts import get_analyzer_prompt
from app.core.logger import logger

class CandidateInfo(BaseModel):
    name: Optional[str] = Field(default="Không rõ", description="Tên ứng viên")
    email: Optional[str] = Field(default="Không rõ", description="Email ứng viên")
    phone: Optional[str] = Field(default="Không rõ", description="Số điện thoại ứng viên")

class CVSchema(BaseModel):
    candidate_info: CandidateInfo = Field(description="Thông tin liên hệ của ứng viên")
    matching_score: int = Field(description="Điểm số phù hợp của CV từ 0 đến 100")
    extracted_skills: List[str] = Field(description="Danh sách các kỹ năng tìm thấy trong CV")
    missing_skills: List[str] = Field(description="Danh sách các kỹ năng còn thiếu")
    suggested_questions: List[str] = Field(description="Danh sách câu hỏi phỏng vấn đề xuất")

class CVAnalyzerAgent:
    async def execute(self, cv_text: str, knowledge: str) -> str:
        if not cv_text:
            return '{"candidate_info":{},"matching_score":0,"extracted_skills":[],"missing_skills":[],"suggested_questions":[]}'
        prompt = get_analyzer_prompt(cv_text, knowledge)
        try:
            llm = get_llm_cheap()
            structured_llm = llm.with_structured_output(CVSchema)
            
            result: CVSchema = await structured_llm.ainvoke([HumanMessage(content=prompt)])
            
            logger.info(" [Analyzer Agent] Bóc tách CV bằng Structured Output thành công!")
            return result.model_dump_json()
            
        except Exception as e:
            logger.error(f"[Analyzer Agent Lỗi]: {e}", exc_info=True)
            return '{"candidate_info":{},"matching_score":0,"extracted_skills":[],"missing_skills":[],"suggested_questions":[]}'