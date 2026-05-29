from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from typing import Optional
from app.services.cv_parser import extract_text_from_cv
from app.services.employer_service import match_cv_to_jd
from app.core.redis_conf import ws_manager
from app.core.logger import logger
import traceback

router = APIRouter()

@router.post("/match")
async def match_cv(
    jd_text: str = Form(..., description="Nội dung Job Description (JD)"),
    cv_file: Optional[UploadFile] = File(None, description="File CV định dạng PDF"),
    cv_id: Optional[str] = Form(None, description="ID của CV đã upload trước đó (tuỳ chọn)")
):
    """
    API đánh giá mức độ phù hợp của ứng viên với Mô tả công việc (JD).
    Có thể truyền trực tiếp file PDF CV hoặc truyền cv_id đã upload trước đó.
    """
    cv_text = ""
    
    try:
        # 1. Lấy text CV
        if cv_file:
            cv_text = await extract_text_from_cv(cv_file)
        elif cv_id and ws_manager.redis_client:
            cv_text_bytes = await ws_manager.redis_client.get(f"cv:{cv_id}")
            if cv_text_bytes:
                cv_text = cv_text_bytes.decode('utf-8') if isinstance(cv_text_bytes, bytes) else cv_text_bytes
        
        if not cv_text:
            raise HTTPException(status_code=400, detail="Không tìm thấy CV text. Vui lòng gửi file CV hoặc cv_id hợp lệ.")
            
        # 2. Rút gọn text nếu quá dài để tránh lỗi token LLM (nếu cần)
        # Giới hạn cơ bản: 15000 ký tự
        if len(cv_text) > 15000:
            cv_text = cv_text[:15000]
            
        if len(jd_text) > 15000:
            jd_text = jd_text[:15000]
            
        # 3. Gọi AI đánh giá
        result = await match_cv_to_jd(cv_text=cv_text, jd_text=jd_text)
        
        return {
            "status": "success",
            "data": result.model_dump()
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[API Employer] Lỗi khi xử lý /match: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
