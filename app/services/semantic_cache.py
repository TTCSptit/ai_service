import uuid
from datetime import datetime, timezone
from langchain_chroma import Chroma
from app.core.embeddings import get_langchain_embeddings
from app.core.config import settings
from app.core.logger import logger
from langsmith import traceable

CACHE_TTL_HOURS = 24


class SemanticCache:
    def __init__(self):
        self.embedding_function = get_langchain_embeddings()

        self.cache_db = Chroma(
            collection_name="semantic_cache",
            embedding_function=self.embedding_function,
            persist_directory="./chroma_memory_db/semantic_cache"
        )

        self.SIMILARITY_THRESHOLD = 0.95

    @traceable(run_type="tool", name="Semantic Cache Check")
    def check_cache(self, user_message: str, user_id: str = "") -> dict:
        """
        Kiểm tra semantic cache.
        
        BUG FIX: Thêm user_id để tránh rò rỉ dữ liệu giữa các user.
        Cache chỉ được hit khi cả nội dung tin nhắn VÀ user_id khớp.
        Nếu user_id rỗng (câu hỏi chung, không liên quan CV cá nhân), 
        cho phép cache toàn cục.
        """
        results = self.cache_db.similarity_search_with_relevance_scores(user_message, k=3)
        if not results:
            return {"is_hit": False, "cached_response": "", "cached_ai_data_json": "{}"}

        for best_match_doc, score in results:
            if score < self.SIMILARITY_THRESHOLD:
                continue

            # BUG FIX: Validate user_id — chặn cache leak giữa các user
            cached_user_id = best_match_doc.metadata.get("user_id", "")
            if user_id and cached_user_id and cached_user_id != user_id:
                logger.warning(
                    f"[Semantic Cache] Bỏ qua cache của user khác "
                    f"(cached_user={cached_user_id}, current_user={user_id}): {user_message[:50]}"
                )
                continue

            # Kiểm tra TTL
            cached_at_str = best_match_doc.metadata.get("cached_at")
            if cached_at_str:
                try:
                    cached_at = datetime.fromisoformat(cached_at_str)
                    age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
                    if age_hours > CACHE_TTL_HOURS:
                        logger.info(
                            f"[Semantic Cache] Expired (age={age_hours:.1f}h > {CACHE_TTL_HOURS}h): "
                            f"{user_message[:50]}"
                        )
                        continue
                except (ValueError, TypeError):
                    pass

            logger.info(f"[Semantic Cache] Hit (score={score:.3f}, user={user_id}): {user_message[:50]}")
            return {
                "is_hit": True,
                "cached_response": best_match_doc.metadata.get("ai_response"),
                "cached_ai_data_json": best_match_doc.metadata.get("ai_data_json", {})
            }

        return {
            "is_hit": False,
            "cached_response": "",
            "cached_ai_data_json": "{}"
        }

    @traceable(run_type="tool", name="Semantic Cache Save")
    def save_cache(self, user_message: str, ai_response: str, ai_data_json: str, user_id: str = ""):
        """
        BUG FIX: Lưu thêm user_id vào metadata để check_cache có thể lọc đúng user.
        """
        safe_user_message = str(user_message) if user_message else ""
        safe_ai_response = str(ai_response) if ai_response is not None else ""
        safe_ai_data_json = str(ai_data_json) if ai_data_json is not None else "{}"

        if not safe_user_message.strip():
            logger.warning("[Semantic Cache] Bỏ qua lưu cache vì user_message rỗng.")
            return

        try:
            self.cache_db.add_texts(
                texts=[safe_user_message],
                metadatas=[
                    {
                        "ai_response": safe_ai_response,
                        "ai_data_json": safe_ai_data_json,
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                        "user_id": str(user_id) if user_id else ""  # BUG FIX: lưu user_id
                    }
                ],
                ids=[str(uuid.uuid4())]
            )
            logger.info(f"[Semantic Cache] Saved (user={user_id}): {safe_user_message[:50]}")
        except Exception as e:
            logger.error(f"[Semantic Cache] Error saving: {e}")


semantic_cache = SemanticCache()