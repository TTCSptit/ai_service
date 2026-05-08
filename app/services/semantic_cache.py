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
    async def check_cache(self, user_message: str, user_id: str = "", cv_hash: str = "", context_hash: str = "") -> dict:
        """
        Kiểm tra semantic cache.
        
        context_hash: Hash của session context hiện tại để tránh hit nhầm context khác.
        """
        # Chroma async search
        results = await self.cache_db.asimilarity_search_with_relevance_scores(user_message, k=5)
        if not results:
            return {"is_hit": False, "cached_response": "", "cached_ai_data_json": "{}"}

        for best_match_doc, score in results:
            if score < self.SIMILARITY_THRESHOLD:
                continue

            # 1. Validate user_id — chặn cache leak giữa các user
            cached_user_id = best_match_doc.metadata.get("user_id", "")
            if user_id and cached_user_id and cached_user_id != user_id:
                continue

            # 2. Validate cv_hash
            cached_cv_hash = best_match_doc.metadata.get("cv_hash", "")
            if cv_hash and cached_cv_hash != cv_hash:
                continue
            
            if not cv_hash and cached_cv_hash:
                continue

            # 3. Validate context_hash (Cực kỳ quan trọng để chống State Poisoning)
            cached_context_hash = best_match_doc.metadata.get("context_hash", "")
            if context_hash and cached_context_hash != context_hash:
                logger.info(f"[Semantic Cache] Bỏ qua vì context_hash không khớp.")
                continue

            # 4. Kiểm tra TTL
            cached_at_str = best_match_doc.metadata.get("cached_at")
            if cached_at_str:
                try:
                    cached_at = datetime.fromisoformat(cached_at_str)
                    age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
                    if age_hours > CACHE_TTL_HOURS:
                        continue
                except (ValueError, TypeError):
                    pass

            logger.info(f"[Semantic Cache] Hit (score={score:.3f}, user={user_id})")
            return {
                "is_hit": True,
                "cached_response": best_match_doc.metadata.get("ai_response"),
                "cached_ai_data_json": best_match_doc.metadata.get("ai_data_json", {})
            }

        return {"is_hit": False, "cached_response": "", "cached_ai_data_json": "{}"}

    @traceable(run_type="tool", name="Semantic Cache Save")
    async def save_cache(self, user_message: str, ai_response: str, ai_data_json: str, user_id: str = "", cv_hash: str = "", context_hash: str = ""):
        """
        Lưu cache kèm theo user_id, cv_hash và context_hash.
        """
        safe_user_message = str(user_message) if user_message else ""
        safe_ai_response = str(ai_response) if ai_response is not None else ""
        safe_ai_data_json = str(ai_data_json) if ai_data_json is not None else "{}"

        if not safe_user_message.strip():
            return

        try:
            # Chroma async add
            await self.cache_db.aadd_texts(
                texts=[safe_user_message],
                metadatas=[
                    {
                        "ai_response": safe_ai_response,
                        "ai_data_json": safe_ai_data_json,
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                        "user_id": str(user_id) if user_id else "",
                        "cv_hash": str(cv_hash) if cv_hash else "",
                        "context_hash": str(context_hash) if context_hash else ""
                    }
                ],
                ids=[str(uuid.uuid4())]
            )
            logger.info(f"[Semantic Cache] Saved (user={user_id}, context={context_hash[:8]})")
        except Exception as e:
            logger.error(f"[Semantic Cache] Error saving: {e}")


semantic_cache = SemanticCache()