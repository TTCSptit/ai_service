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
