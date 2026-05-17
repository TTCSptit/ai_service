from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import httpx
import tempfile
import os
from app.agents.audio_analyzer_agent import AudioAnalyzerAgent
from app.core.logger import logger

router = APIRouter()
audio_agent = AudioAnalyzerAgent()

class AnalyzeAudioRequest(BaseModel):
    room_id: str
    audio_url: str

@router.post("/interview/analyze-audio")
async def analyze_audio(request: AnalyzeAudioRequest, background_tasks: BackgroundTasks):
    """
    Webhook do Backend C# gọi sang kèm file âm thanh phỏng vấn.
    """
    # Chạy ngầm để không block request Webhook
    background_tasks.add_task(process_audio_task, request.room_id, request.audio_url)
    return {"status": "processing", "room_id": request.room_id}

async def process_audio_task(room_id: str, audio_url: str):
    logger.info(f"[Interview API] Bắt đầu xử lý audio cho phòng {room_id} từ {audio_url}")
    tmp_path = None
    try:
        # Download audio file
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
                tmp_file.write(resp.content)
                tmp_path = tmp_file.name

        # Bóc băng và Phân tích LLM
        result = await audio_agent.analyze_interview_audio(tmp_path, room_id)
        
        # Cleanup
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            
        logger.info(f"[Interview API] Xử lý xong phòng {room_id}. Điểm giao tiếp: {result['communication_score']}")
        
        # TODO: Ở đây có thể gửi kết quả này ngược lại cho Backend C# lưu DB 
        # (Ví dụ: POST /api/profiles/interview-report)
        
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        logger.error(f"[Interview API Lỗi] {e}")


class SimulateRequest(BaseModel):
    room_id: str
    transcript: str | None = None

@router.post("/interview/simulate-analysis")
async def simulate_analysis(request: SimulateRequest):
    """
    Giả lập chấm điểm cuộc phỏng vấn dựa trên kịch bản văn bản tiếng Việt có sẵn.
    Dùng để test tính năng đánh giá Llama3 local Kaggle trực tiếp từ UI.
    """
    transcript = request.transcript
    if not transcript:
        # Kịch bản giả lập cực kỳ chân thực của sinh viên PTIT đi phỏng vấn React
        transcript = """
        Người phỏng vấn: Chào em, em giới thiệu bản thân một chút nhé.
        Ứng viên: Dạ em chào anh... Em tên là Nam, sinh viên năm 4 khoa CNTT học viện Công nghệ Bưu chính Viễn thông ạ. Em có tìm hiểu về ReactJS được khoảng 6 tháng và đã làm một số dự án clone nhỏ trên Github ạ.
        Người phỏng vấn: Tốt. Vậy em cho anh hỏi, trong ReactJS, sự khác nhau giữa useEffect và useMemo là gì? Khi nào thì nên dùng useMemo?
        Ứng viên: Dạ... em nhớ là useEffect dùng để chạy các hiệu ứng phụ (side effects) như là gọi API khi component render. Còn useMemo... hình như là để tối ưu hóa hiệu năng, nó lưu lại giá trị tính toán. Nhưng em... em chưa dùng useMemo trong dự án thực tế bao giờ, chỉ xem lý thuyết thôi ạ.
        Người phỏng vấn: Ừm, thế còn việc truyền props qua nhiều tầng (prop drilling) thì em giải quyết thế nào trong React?
        Ứng viên: Dạ em sẽ dùng React Context API để truyền dữ liệu trực tiếp xuống component con mà không cần qua các tầng trung gian ạ. Hoặc nếu dự án lớn thì dùng Redux ạ.
        Người phỏng vấn: Khá tốt. Em có biết về Virtual DOM hoạt động thế nào không?
        Ứng viên: Dạ Virtual DOM là một bản sao gọn nhẹ của DOM thật. Khi state thay đổi, React sẽ tạo ra Virtual DOM mới, so sánh (diffing) với bản cũ để tìm ra phần thay đổi, rồi chỉ cập nhật phần đó lên DOM thật để tăng tốc độ render ạ.
        Người phỏng vấn: Câu trả lời rất chuẩn. Cảm ơn em.
        """
    
    result = await audio_agent.analyze_interview_transcript(transcript)
    return result
