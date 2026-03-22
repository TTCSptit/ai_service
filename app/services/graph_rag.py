import os
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from app.core.llm import get_llm_vip
from app.core.logger import logger

os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password123"

try:
    graph = Neo4jGraph()
except Exception as e:
    logger.error(f"Lỗi kết nối Neo4j từ GraphRAG: {e}")
    graph = None

async def query_knowledge_graph(user_question: str)->str:
    if not graph:
        return ""
    logger.info(f"[GraphRAG] Đang truy vấn đồ thị cho câu hỏi: {user_question}")
    try:
        chain = GraphCypherQAChain.from_llm(
            llm=get_llm_vip(), 
            graph=graph, 
            verbose=True, 
            allow_dangerous_requests=True,
            top_k=3
        )
        
        response = await chain.ainvoke({"query": user_question})
        result_text = response.get("result", "")
        
        logger.info(f"[GraphRAG] Kết quả rút ra từ Đồ thị: {result_text}")
        return result_text
        
    except Exception as e:
        logger.warning(f"[GraphRAG] AI không tìm thấy chuỗi liên kết đồ thị phù hợp: {e}")
        return "" 