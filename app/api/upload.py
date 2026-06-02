import uuid
from fastapi import APIRouter, File, UploadFile, Depends
from app.services.cv_parser import extract_text_from_cv
from app.core.redis_conf import ws_manager
from app.prompts.system_prompts import sanitize_input
from app.core.logger import logger
import json

router = APIRouter()

@router.post("/cv/upload")
async def upload_cv(cv_file: UploadFile = File(...)):
    """API Upload CV. Phân tích text và lưu tạm vào Redis."""
    try:
        cv_text = await extract_text_from_cv(cv_file)
        if cv_text:
            cv_text = sanitize_input(cv_text, max_length=10000)
            
            cv_id = str(uuid.uuid4())
            
            from app.core.config import settings
            import redis.asyncio as redis
            
            r_client = ws_manager.redis_client
            temp_client = False
            
            if not r_client and settings.REDIS_URL:
                try:
                    r_client = redis.from_url(settings.REDIS_URL, decode_responses=True, ssl_cert_reqs="none")
                    temp_client = True
                except Exception as e:
                    logger.error(f"[Upload] Lỗi tạo Redis client tạm: {e}")
                    
            if r_client:
                try:
                    await r_client.setex(f"cv:{cv_id}", 7200, cv_text)
                    return {"cv_id": cv_id, "message": "Upload CV thành công"}
                except Exception as e:
                    logger.error(f"[Upload] Lỗi khi lưu vào Redis: {e}")
                    return {"cv_id": "", "error": f"Lỗi lưu Redis: {str(e)}"}
                finally:
                    if temp_client:
                        await r_client.close()
            else:
                return {"cv_id": "", "error": "Redis chưa được cấu hình hoặc không thể kết nối"}
        return {"cv_id": "", "error": "Không thể trích xuất text từ CV"}
    except Exception as e:
        logger.error(f"[Upload] Lỗi phân tích CV: {e}")
        return {"cv_id": "", "error": str(e)}
