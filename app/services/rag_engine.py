import os
import chromadb
from chromadb.utils import embedding_functions
import asyncio
from typing import List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.core.llm import get_llm_cheap
from app.core.logger import logger
BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "vector_db")
DATA_PATH = os.path.join(BASE_DIR, "data")

chroma_client = chromadb.PersistentClient(path=DB_PATH)
embedding_fn = None
collection = None

def get_collection():
    global embedding_fn, collection
    if collection is None:
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        collection = chroma_client.get_or_create_collection(
            name="career_knowledge", embedding_function=embedding_fn
        )
    return collection


def init_database():
    col = get_collection()
    if col.count() == 0:
        if not os.path.exists(DATA_PATH):
            os.makedirs(DATA_PATH)

        documents = []
        metadatas = []
        ids = []

        for filename in os.listdir(DATA_PATH):
            if filename.endswith((".txt", ".md")):
                file_path = os.path.join(DATA_PATH, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    if text.strip():
                        documents.append(text)
                        metadatas.append({"source": filename})
                        ids.append(filename)
        if documents:
            col.add(documents=documents, metadatas=metadatas, ids=ids)
            print("nap success")
        else:
            print("nap failue")


"""Hàm tìm kiếm tài liệu liên quan đến câu hỏi của người dùng"""

class QueryVariations(BaseModel):
    queries: List[str]= Field(
        description="Danh sách 3 phiên bản viết lại của câu hỏi gốc, dùng từ khóa chuyên ngành IT, mở rộng ngữ cảnh."       
    )
async def generate_multi_queries(original_query: str) ->List[str]:
    prompt = f"""Bạn là một chuyên gia tra cứu tài liệu IT.
    Người dùng đang hỏi: "{original_query}"
    Nhiệm vụ: Viết lại câu hỏi này thành 3 phiên bản khác nhau để tối ưu hóa việc tìm kiếm trong Vector Database. 
    Ví dụ: "Docker là gì?" -> ["Định nghĩa Containerization và Docker", "Ứng dụng của Docker trong CI/CD DevOps", "Kiến trúc hoạt động của Docker engine"]."""
    try:
        llm = get_llm_cheap()
        structured_llm =  llm.with_structured_output(QueryVariations)
        result: QueryVariations = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        return result.queries
    except Exception as e:
        logger.error(f"[Multi-Query Lỗi]: {e}")
        
        return []
async def search_knowledge_advanced(query: str, k: int = 2) -> str:
    col = get_collection()
    if col.count() == 0:
        return ""
    logger.info(f"[RAG] Bắt đầu tìm kiếm Multi-Query cho: {query}")

    variations = await generate_multi_queries(query)
    all_queries = [query] + variations
    logger.info(f"[RAG] Đã phân thân thành {len(all_queries)} luồng tìm kiếm!")

    # FIX Bug 8: dùng dict để lưu cả doc và distance score tốt nhất (thấp nhất)
    RELEVANCE_THRESHOLD = 1.2  # L2 distance — thấp hơn = liên quan hơn
    best_docs: dict[str, float] = {}  # {content: best_distance}

    for q in all_queries:
        if not q.strip():
            continue

        results = col.query(
            query_texts=[q],
            n_results=k,
            include=["documents", "distances"]  # FIX: lấy distances để filter
        )

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, dist in zip(docs, distances):
            content = getattr(doc, "page_content", doc)
            # Chỉ giữ nếu đủ liên quan, hoặc nếu tìm thấy match tốt hơn
            if dist <= RELEVANCE_THRESHOLD:
                if content not in best_docs or dist < best_docs[content]:
                    best_docs[content] = dist

    # Sắp xếp theo độ liên quan (distance thấp nhất trước)
    sorted_docs = sorted(best_docs.items(), key=lambda x: x[1])
    best_contexts = [doc for doc, _ in sorted_docs[:4]]

    if not best_contexts:
        logger.warning(f"[RAG] Không tìm thấy tài liệu nào đủ liên quan (threshold={RELEVANCE_THRESHOLD}).")
        return ""

    result_text = "\n---\n".join(best_contexts)
    logger.info(f"[RAG] Gom thành công {len(best_contexts)} đoạn tài liệu cốt lõi (sau khi filter score).")
    
    return result_text



def search_knowledge(query: str, n_results: int = 1) -> str:
    col = get_collection()
    if col.count() == 0:
        return ""

    results = col.query(query_texts=[query], n_results=n_results)
    if results["documents"] and results["documents"][0]:
        return "\n".join(results["documents"][0])
    return ""
