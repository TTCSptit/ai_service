import uuid
from fastapi import APIRouter, File, UploadFile, Depends
from fastapi_limiter.depends import RateLimiter
from app.services.cv_parser import extract_text_from_cv
from app.core.redis_conf import ws_manager
from app.prompts.system_prompts import sanitize_input
from app.core.logger import logger
import json

router = APIRouter()

@router.post("/cv/upload", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def upload_cv(cv_file: UploadFile = File(...)):
    """API Upload CV. Phân tích text và lưu tạm vào Redis."""
    try:
        cv_text = await extract_text_from_cv(cv_file)
        if cv_text:
            cv_text = sanitize_input(cv_text, max_length=10000)
            
            cv_id = str(uuid.uuid4())
            if ws_manager.redis_client:
                await ws_manager.redis_client.setex(f"cv:{cv_id}", 7200, cv_text)
                return {"cv_id": cv_id, "message": "Upload CV thành công"}
            else:
                return {"cv_id": "", "error": "Redis chưa được cấu hình"}
        return {"cv_id": "", "error": "Không thể trích xuất text từ CV"}
    except Exception as e:
        logger.error(f"[Upload] Lỗi phân tích CV: {e}")
        return {"cv_id": "", "error": str(e)}
