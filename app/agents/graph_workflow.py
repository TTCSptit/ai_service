import asyncio
from langgraph.graph import StateGraph, END
from app.agents.graph_state import AgentState

from app.agents.router_agent import RouterAgent
from app.agents.analyzer_agent import CVAnalyzerAgent
from app.agents.evaluator_agent import TechLeadEvaluator
from app.agents.market_agent import MarketAnalyzerAgent
from app.prompts.system_prompts import get_hr_advisor_prompt, get_final_revision_prompt
from app.core.logger import logger
from app.services.graph_rag import query_knowledge_graph
router_agent = RouterAgent()
analyzer_agent = CVAnalyzerAgent()
evaluator_agent = TechLeadEvaluator()
market_agent = MarketAnalyzerAgent()

async def node_prepare_context(state: AgentState):
    logger.info("[Node 1] Đang chuẩn bị Context...")
    router_decision = await router_agent.execute(state["message"])
    is_valid_topic = router_decision.get("is_valid_topic", True)
    
    if not is_valid_topic:
        logger.warning("[Router Guardrail] Câu hỏi ngoài lề. Chặn luồng xử lý RAG/LLM.")
        return {
            "internet_context": "",
            "market_context": "",
            "ai_data_json": '{"candidate_info":{},"matching_score":0,"extracted_skills":[],"missing_skills":[],"suggested_questions":[]}',
            "graph_context": "",
            "system_prompt_ref": "Bạn là AI hỗ trợ nhân sự và công nghệ. Câu hỏi của người dùng ngoài luồng công việc (phiếm chuyện/chitchat). Hãy từ chối trả lời lịch sự, thân thiện và hướng họ quay lại các chủ đề như tư vấn lộ trình học, review đánh giá CV kỹ năng lập trình hoặc phỏng vấn thử (Mock Interview).",
            "user_prompt_ref": state["message"],
            "retry_count": 0,
            "draft_text": "",
            "feedback": "",
            "eval_pass": True,
            "final_prompt": "",
            "is_valid_topic": False
        }
        
    internet_ctx = router_decision.get("internet_context", "")
    
    task_analyzer = analyzer_agent.execute(state["cv_text"], state["knowledge"]) if (router_decision.get("needs_cv") and state["cv_text"]) else asyncio.sleep(0)
    task_graph = query_knowledge_graph(state["message"]) if router_decision.get("needs_graph") else asyncio.sleep(0)
    task_market = market_agent.execute(state["message"]) if router_decision.get("needs_market_data") else asyncio.sleep(0)
    
    results = await asyncio.gather(task_analyzer, task_graph, task_market)
    
    ai_json = results[0] if (router_decision.get("needs_cv") and state["cv_text"]) else '{"candidate_info":{},"matching_score":0,"extracted_skills":[],"missing_skills":[],"suggested_questions":[]}'
    graph_ctx = results[1] if router_decision.get("needs_graph") else ""
    market_ctx = results[2] if router_decision.get("needs_market_data") else ""
    
    sys_prompt = get_hr_advisor_prompt(state["knowledge"],state["user_memory"])
    if state["session_summary"]:
        sys_prompt += f"\n\n[BIÊN BẢN SESSION]\n{state['session_summary']}"
        
    usr_prompt = f"Câu hỏi hiện tại: {state['message']}\n"
    if internet_ctx: usr_prompt += f"[Thông tin Internet]: {internet_ctx}\n"
    if graph_ctx: usr_prompt += f"[Kiến thức từ Graph Database]: {graph_ctx}\n" 
    if market_ctx: usr_prompt += f"[Dữ liệu Thị trường thực tế]: {market_ctx}\n"

    return {
        "internet_context": internet_ctx,
        "market_context": market_ctx,
        "ai_data_json": ai_json,
        "graph_context": graph_ctx,
        "system_prompt_ref": sys_prompt,
        "user_prompt_ref": usr_prompt,
        "retry_count": 0,
        "is_valid_topic": True
    }
async def node_drafring(state: AgentState):
    logger.info("[Node 2] Đang viết nháp (Lần {state['retry_count'] + 1})...")
    draft = await evaluator_agent.generate_draft(
        state["history"],state["system_prompt_ref"],state["user_prompt_ref"]
    )
    return {"draft_text": draft, "retry_count": state["retry_count"] + 1}
async def node_evaluating(state:AgentState):
    logger.info("[Node 3] Tech Lead đang chấm điểm...")
    is_pass,feedback = await evaluator_agent.evaluate(state["message"],state["draft_text"])
    logger.info(f"[Tech Lead]: Pass={is_pass} | Feedback: {feedback}")
    return {"eval_pass": is_pass, "feedback": feedback}

async def node_revising(state:AgentState):
    logger.warning("[Node 4] Bị chê, đang viết lại nháp...")
    revised_user_prompt = state["user_prompt_ref"] + f"\n[Tech Lead Feedback Cần Sửa]: {state['feedback']}"
    draft = await evaluator_agent.generate_draft(state["history"], state["system_prompt_ref"], revised_user_prompt)
    return {"draft_text": draft, "retry_count": state["retry_count"] + 1}
def should_continue_loop(state: AgentState):
    if state["eval_pass"]:
        return "approved"
    if state["retry_count"] >= 2:
        logger.warning("Đã hết số lần sửa tối đa. Buộc xuất xưởng.")
        return "approved"
    return "rejected"

async def node_finalize(state: AgentState):
    logger.info("[Node Cuối] Đóng gói gửi cho VIP AI phát sóng...")
    final_prompt = get_final_revision_prompt(state["system_prompt_ref"], state["feedback"], state["draft_text"])
    return {"final_prompt": final_prompt}

workflow = StateGraph(AgentState)

workflow.add_node("prepare",node_prepare_context)
workflow.add_node("draft",node_drafring)
workflow.add_node("evaluate",node_evaluating)
workflow.add_node("revise",node_revising)
workflow.add_node("finalize",node_finalize)

def should_continue_from_prepare(state: AgentState):
    if state.get("is_valid_topic", True) == False:
        logger.warning("Bỏ qua đánh giá, rẽ nhánh thẳng đến điểm kết thúc.")
        return "end"
    return "draft"

workflow.set_entry_point("prepare")

workflow.add_conditional_edges(
    "prepare",
    should_continue_from_prepare,
    {
        "draft": "draft",
        "end": END
    }
)
workflow.add_edge("draft","evaluate")

workflow.add_conditional_edges(
    "evaluate",
    should_continue_loop,
    {
        "approved":"finalize",
        "rejected":"revise"
    }
)
workflow.add_edge("revise", "evaluate") 
workflow.add_edge("finalize", END)

app_graph = workflow.compile()