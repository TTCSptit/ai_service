from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from app.core.config import settings
from app.core.llm import get_llm_vip, get_llm_cheap
from app.core.logger import logger

import asyncio

_qa_chain = None
_graph = None
_is_initialized = False

def get_qa_chain():
    """Hàm khởi tạo lazy (Lazy Initialization) cho Neo4j và QA Chain"""
    global _qa_chain, _graph, _is_initialized
    
    if not _is_initialized:
        try:
            logger.info("[GraphRAG] Bắt đầu kết nối Neo4j và khởi tạo Chain (Lazy Load)...")
            _graph = Neo4jGraph(
                url=settings.NEO4J_URI,
                username=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD
            )
            _qa_chain = GraphCypherQAChain.from_llm(
                llm=get_llm_vip(),           
                cypher_llm=get_llm_cheap(),  
                graph=_graph, 
                verbose=True, 
                allow_dangerous_requests=True,
                validate_cypher=True,        
                top_k=7,
                return_direct=True         
            )
            logger.info("[GraphRAG] Khởi tạo thành công Neo4j QA Chain.")
        except Exception as e:
            logger.error(f"Lỗi kết nối hoặc khởi tạo Neo4j: {e}")
            _graph = None
            _qa_chain = None
        finally:
            _is_initialized = True
            
    return _qa_chain

def _run_graph_query_sync(user_question: str) -> str:
    """Hàm chạy đồng bộ (Synchronous) thực hiện gọi Neo4j"""
    chain = get_qa_chain()
    
    if not chain:
        return ""
        
    try:
        response = chain.invoke({"query": user_question})
        raw_result = response.get("result", "")
        
        result_text = str(raw_result)
        
        if not raw_result or result_text == "[]" or "I don't know" in result_text:
            return ""
        
        logger.info(f"[GraphRAG] Kết quả rút ra từ Đồ thị: {result_text}")
        return result_text
    except Exception as e:
        logger.warning(f"[GraphRAG] Lỗi truy vấn dữ liệu: {e}")
        return ""

async def query_knowledge_graph(user_question: str)->str:
    logger.info(f"[GraphRAG] Đang truy vấn đồ thị cho câu hỏi: {user_question}")
    
    result = await asyncio.to_thread(_run_graph_query_sync, user_question)
    return result