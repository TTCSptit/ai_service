import os
from groq import Groq
from app.core.config import settings
from app.core.llm import get_llm_kaggle_v1
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.core.logger import logger

class InterviewReport(BaseModel):
    communication_score: int = Field(description="Điểm giao tiếp (0-100)")
    technical_score: int = Field(description="Điểm kỹ thuật/chuyên môn (0-100)")
    confidence_score: int = Field(description="Điểm tự tin (0-100)")
    feedback_strengths: list[str] = Field(description="Danh sách điểm mạnh của ứng viên")
    feedback_weaknesses: list[str] = Field(description="Danh sách điểm yếu cần khắc phục")
    transcript_summary: str = Field(description="Tóm tắt ngắn gọn nội dung cuộc phỏng vấn")

class AudioAnalyzerAgent:
    def __init__(self):
        # Groq Client gốc (để dùng Whisper, langchain-groq chưa hỗ trợ audio)
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        
    async def analyze_interview_audio(self, file_path: str, room_id: str) -> dict:
        try:
            logger.info(f"[AudioAnalyzer] Đang gọi Whisper bóc băng file: {file_path}")
            # 1. Speech-to-Text via Groq Whisper API
            with open(file_path, "rb") as file:
                # API Whisper của Groq yêu cầu truyền file dạng tuple (filename, file_object)
                transcription = self.groq_client.audio.transcriptions.create(
                  file=(os.path.basename(file_path), file.read()),
                  model="whisper-large-v3",
                  response_format="text",
                  language="vi" # Ưu tiên tiếng Việt
                )
            
            transcript_text = transcription
            logger.info(f"[AudioAnalyzer] Bóc băng thành công ({len(transcript_text)} ký tự)")
            
            # 2. LLM Analysis
            logger.info(f"[AudioAnalyzer] Đang dùng LLM chấm điểm phỏng vấn...")
            prompt = f"""Dưới đây là kịch bản bóc băng (transcript) của một cuộc phỏng vấn xin việc (Video Call).
            Hãy phân tích và chấm điểm ứng viên dựa trên cuộc đối thoại này:
            
            [TRANSCRIPT BÓC BĂNG BỞI AI]
            {transcript_text}
            
            Nhiệm vụ của bạn (HR & Tech Lead):
            1. Đánh giá sự tự tin (dựa vào ngôn từ, cách nói dứt khoát hay ngập ngừng, lặp từ).
            2. Đánh giá kỹ năng giao tiếp (chào hỏi, logic trình bày).
            3. Đánh giá kỹ năng chuyên môn (kiểm tra xem ứng viên trả lời đúng hay sai).
            
            Lưu ý: Văn bản bóc băng có thể không ghi rõ ai là người nói, bạn phải tự suy luận ai là ứng viên (thường là người trả lời) và ai là HR (người đặt câu hỏi).
            """
            
            structured_llm = get_llm_kaggle_v1().with_structured_output(InterviewReport)
            report: InterviewReport = await structured_llm.ainvoke([HumanMessage(content=prompt)])
            
            logger.info(f"[AudioAnalyzer] Hoàn tất chấm điểm. Điểm giao tiếp: {report.communication_score}")
            return report.model_dump()
            
        except Exception as e:
            logger.error(f"[AudioAnalyzer Lỗi]: {str(e)}")
            raise e
