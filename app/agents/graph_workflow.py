import asyncio
from langgraph.graph import StateGraph, END
from app.agents.graph_state import AgentState

from app.agents.router_agent import RouterAgent
from app.agents.analyzer_agent import CVAnalyzerAgent
from app.agents.evaluator_agent import TechLeadEvaluator
from app.prompts.system_prompts import get_hr_advisor_prompt, get_final_revision_prompt
from app.core.logger import logger
from app.services.graph_rag import query_knowledge_graph
router_agent = RouterAgent()
analyzer_agent = CVAnalyzerAgent()
evaluator_agent = TechLeadEvaluator()

async def node_prepare_context(state: AgentState):
    logger.info("[Node 1] Đang chuẩn bị Context...")
    router_decision = await router_agent.execute(state["message"])
    internet_ctx = router_decision.get("internet_context", "")
    
    task_analyzer = analyzer_agent.execute(state["cv_text"], state["knowledge"]) if (router_decision.get("needs_cv") and state["cv_text"]) else asyncio.sleep(0)
    task_graph = query_knowledge_graph(state["message"]) if router_decision.get("needs_graph") else asyncio.sleep(0)
    
    results = await asyncio.gather(task_analyzer, task_graph)
    
    ai_json = results[0] if (router_decision.get("needs_cv") and state["cv_text"]) else '{"candidate_info":{},"matching_score":0,"extracted_skills":[],"missing_skills":[],"suggested_questions":[]}'
    graph_ctx = results[1] if router_decision.get("needs_graph") else ""
    
    sys_prompt = get_hr_advisor_prompt(state["knowledge"],state["user_memory"])
    if state["session_summary"]:
        sys_prompt += f"\n\n[BIÊN BẢN SESSION]\n{state['session_summary']}"
        
    usr_prompt = f"Câu hỏi hiện tại: {state['message']}\n"
    if internet_ctx: usr_prompt += f"[Thông tin Internet]: {internet_ctx}\n"
    if graph_ctx: usr_prompt += f"[Kiến thức từ Graph Database]: {graph_ctx}\n" # BƠM KIẾN THỨC ĐỒ THỊ VÀO
    if state["cv_text"]: usr_prompt += f"CV:\n{state['cv_text']}"

    return {
        "internet_context": internet_ctx,
        "ai_data_json": ai_json,
        "graph_context": graph_ctx,
        "system_prompt_ref": sys_prompt,
        "user_prompt_ref": usr_prompt,
        "retry_count": 0
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

workflow.set_entry_point("prepare")
workflow.add_edge("prepare","draft")
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