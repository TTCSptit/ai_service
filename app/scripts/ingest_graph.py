import os
import asyncio
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j import Neo4jGraph

from app.core.llm import get_llm_vip
from app.core.logger import logger
from app.core.config import settings

NEO4J_URI = settings.NEO4J_URI
NEO4J_USERNAME = settings.NEO4J_USERNAME
NEO4J_PASSWORD = settings.NEO4J_PASSWORD
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "f7d40e28")

async def ingest_data_folder(folder_path: str):
    
    if not os.path.exists(folder_path):
        logger.error(f"Thư mục không tồn tại: {folder_path}")
        return

    files = [f for f in os.listdir(folder_path) if f.endswith((".txt", ".md"))]
    if not files:
        logger.warning(f"Không tìm thấy file .txt hoặc .md nào trong {folder_path}")
        return

    logger.info(f"[Graph Ingest] Tìm thấy {len(files)} file (.txt, .md). Bắt đầu xử lý nạp liệu hàng loạt...")
    
    try:
        graph = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=NEO4J_DATABASE
        )
        
        llm = get_llm_vip()
        llm_transformer = LLMGraphTransformer(
            llm=llm,
            allowed_nodes=["Technology", "Skill", "Concept", "Role", "Tool", "Company", "Framework", "Language"], 
            allowed_relationships=["USES", "REQUIRES", "IS_A", "DEVELOPED_BY", "PART_OF", "WORKS_WITH", "LEARN_PATH"]
        )

        for filename in files:
            file_path = os.path.join(folder_path, filename)
            logger.info(f"--- Đang xử lý: {filename} ---")
            
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                documents = loader.load()
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                chunks = text_splitter.split_documents(documents)
                
                graph_documents = llm_transformer.convert_to_graph_documents(chunks)
                
                graph.add_graph_documents(
                    graph_documents, 
                    baseEntityLabel=True, 
                    include_source=True
                )
                logger.info(f"Đã nạp xong: {filename}")
            except Exception as e:
                logger.error(f"Lỗi tại file {filename}: {e}")

        logger.info("[Graph Ingest] HOÀN TẤT NẠP DỮ LIỆU THƯ MỤC! ")

    except Exception as e:
        logger.error(f"[Graph Ingest] Lỗi kết nối hoặc hệ thống: {e}")

if __name__ == "__main__":
    import sys
    target_folder = sys.argv[1] if len(sys.argv) > 1 else "data"
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        with open(os.path.join(target_folder, "sample.txt"), "w", encoding="utf-8") as f:
            f.write("Python is a programming language used for AI development. Neo4j is a graph database.")

    asyncio.run(ingest_data_folder(target_folder))
