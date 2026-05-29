from pydantic import BaseModel, Field
from typing import List

class MatchResponse(BaseModel):
    score: int = Field(description="Điểm số đánh giá mức độ phù hợp của CV với JD, từ 0 đến 100")
    strengths: List[str] = Field(description="Danh sách các điểm mạnh của ứng viên so với JD (tối đa 3-5 điểm)")
    weaknesses: List[str] = Field(description="Danh sách các điểm yếu hoặc kỹ năng còn thiếu của ứng viên so với JD (tối đa 3-5 điểm)")
    reasoning: str = Field(description="Đoạn văn ngắn gọn giải thích lý do cho điểm số này")
