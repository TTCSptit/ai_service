import os
from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from app.core.config import settings
from app.core.llm import get_llm_vip 
from app.core.logger import logger

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password123"

try:
    graph = Neo4jGraph()
    logger.info("Đã kết nối thành công tới Neo4j!")
except Exception as e:
    logger.error(f" Lỗi kết nối Neo4j: {e}")
    exit()


llm_transformer = LLMGraphTransformer(
    llm=get_llm_vip(),
    allowed_nodes=["Technology", "Skill", "Role", "Concept", "Tool"],
    allowed_relationships=["REQUIRES", "USES", "PART_OF", "HELPS_WITH", "RELATED_TO"]
)

def build_knowledge_graph(file_path: str):
    logger.info(f"Đang đọc tài liệu từ: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text_data = f.read()
    except FileNotFoundError:
        logger.error("Không tìm thấy file tài liệu!")
        return

    documents = [Document(page_content=text_data)]

    logger.info("AI đang phân tích và trích xuất Entity-Relationship... (Sẽ mất vài phút)")
    
    try:
        graph_documents = llm_transformer.convert_to_graph_documents(documents)
        
        logger.info(f"Đã trích xuất được {len(graph_documents[0].nodes)} Nodes và {len(graph_documents[0].relationships)} Quan hệ!")
        
        graph.add_graph_documents(graph_documents, baseEntityLabel=True, include_source=True)
        
        logger.info("Đã lưu thành công Knowledge Graph vào Neo4j!")
    except Exception as e:
        logger.error(f"Lỗi trong quá trình bóc tách đồ thị: {e}", exc_info=True)

import os

if __name__ == "__main__":
    data_folder = "data"

    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

        with open(os.path.join(data_folder, "sample.txt"), "w", encoding="utf-8") as f:
            f.write(
                "Kỹ sư Frontend cần thành thạo ReactJS và TypeScript. "
                "ReactJS giúp xây dựng giao diện UI. "
                "TypeScript bổ sung type checking cho JavaScript. "
                "Kỹ năng phụ trợ bao gồm Redux để quản lý State."
            )

    for file in os.listdir(data_folder):
        file_path = os.path.join(data_folder, file)

        if os.path.isfile(file_path):
            print(f"Processing: {file_path}")
            build_knowledge_graph(file_path)