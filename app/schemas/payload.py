from pydantic import BaseModel, Field
from typing import Optional, List
        
class ChatRequestJSON(BaseModel):
    message: str =Field(...,min_length=2,description="Câu hỏi của ứng viên")
    target_job:Optional[str]=Field(None,description="Vị trí ứng viên muốn nhắm tới (VD: Frontend, Backend)")
class CandidateInfo(BaseModel):
    name: Optional[str] = Field(default=None, description="Tên ứng viên")
    email: Optional[str] = Field(default=None, description="Email ứng viên")
    phone: Optional[str] = Field(default=None, description="Số điện thoại")
class AIChatResponse(BaseModel):
    sessionId: str = Field(...,description="Mã phiên chat")
    reply: str =Field(
        ...,
        description="Câu trả lời tư vấn chi tiết từ Bot"
    )
    has_cv: bool =Field(
        default=False,
        description="Cờ xác nhận hệ thống có đọc được CV hay không"
    )
    suggested_questions: List[str] = Field(default=[])

    candidate_info: Optional[CandidateInfo] = Field(default=None, description="Thông tin cá nhân trích xuất từ CV")
    extracted_skills: List[str] = Field(default=[], description="Kỹ năng AI quét được trong CV")
    missing_skills: List[str] = Field(default=[], description="Kỹ năng ứng viên còn thiếu so với RAG")
    matching_score:Optional[int]= Field(
        default=None,
        description="Điểm đánh giá độ phù hợp của CV với lộ trình (0-100)",
        ge=0,le=100
    )

