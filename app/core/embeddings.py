from langchain_huggingface import HuggingFaceEmbeddings

class SharedEmbeddings:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            print("[System] Đang khởi tạo mô hình Embedding (chỉ chạy 1 lần)...")
            cls._instance = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2"
            )
            print("[System] Khởi tạo Embedding thành công!")
        return cls._instance

class ChromaNativeEmbeddingWrapper:
    """Wrapper để tương thích với ChromaDB native client (dùng trong rag_engine.py)"""
    def __init__(self, langchain_embeddings):
        self.embeddings = langchain_embeddings
    
    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embeddings.embed_documents(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self.__call__(input)

    def name(self) -> str:
        return "sentence_transformer"

def get_langchain_embeddings():
    """Dùng cho Langchain (như MemoryAgent, SemanticCache)"""
    return SharedEmbeddings.get_instance()

def get_chroma_native_embeddings():
    """Dùng cho ChromaDB Native Client (như RAG Engine)"""
    return ChromaNativeEmbeddingWrapper(SharedEmbeddings.get_instance())
