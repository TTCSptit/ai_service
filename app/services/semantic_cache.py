import uuid
from datetime import datetime, timezone
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import settings
from app.core.logger import logger

# FIX Bug 4: Thêm TTL cho cache — entries cũ hơn CACHE_TTL_HOURS sẽ bị bỏ qua
CACHE_TTL_HOURS = 24


class SemanticCache:
    def __init__(self):
        self.embedding_function = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )

        self.cache_db = Chroma(
            collection_name="semantic_cache",
            embedding_function=self.embedding_function,
            persist_directory="./chroma_memory_db/semantic_cache"
        )

        self.SIMILARITY_THRESHOLD = 0.95

    def check_cache(self, user_message: str) -> dict:
        results = self.cache_db.similarity_search_with_relevance_scores(user_message, k=1)
        if results:
            best_match_doc, score = results[0]
            if score >= self.SIMILARITY_THRESHOLD:
                # FIX Bug 4: Kiểm tra TTL — bỏ qua nếu cache đã quá cũ
                cached_at_str = best_match_doc.metadata.get("cached_at")
                if cached_at_str:
                    try:
                        cached_at = datetime.fromisoformat(cached_at_str)
                        age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
                        if age_hours > CACHE_TTL_HOURS:
                            logger.info(f"[Semantic Cache] Expired (age={age_hours:.1f}h > {CACHE_TTL_HOURS}h): {user_message[:50]}")
                            return {"is_hit": False, "cached_response": "", "cached_ai_data_json": "{}"}
                    except (ValueError, TypeError):
                        pass  # Nếu lỗi parse timestamp, bỏ qua check TTL

                logger.info(f"[Semantic Cache] Hit (score={score:.3f}): {user_message[:50]}")
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

    def save_cache(self, user_message: str, ai_response: str, ai_data_json: str):
        try:
            self.cache_db.add_documents(
                documents=[user_message],
                metadatas=[
                    {
                        "ai_response": ai_response,
                        "ai_data_json": ai_data_json,
                        "cached_at": datetime.now(timezone.utc).isoformat()  # FIX Bug 4: lưu timestamp
                    }
                ],
                ids=[str(uuid.uuid4())]
            )
            logger.info(f"[Semantic Cache] Saved: {user_message[:50]}")
        except Exception as e:
            logger.error(f"[Semantic Cache] Error saving: {e}")


semantic_cache = SemanticCache()