from typing import TypedDict, List
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    message: str
    cv_text: str
    history: List[BaseMessage]
    user_memory: str
    session_summary: str
    knowledge: str
    graph_context:str
    internet_context: str
    ai_data_json: str
    
    system_prompt_ref: str  
    user_prompt_ref: str   
    draft_text: str
    feedback: str
    eval_pass: bool
    retry_count: int
    
    final_prompt: str