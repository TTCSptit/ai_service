import json
import pytest
import asyncio
from pathlib import Path

# Fix relative import path for testing
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agents.graph_workflow import app_graph

# Load test cases
test_cases_path = Path(__file__).parent / "test_cases.json"
with open(test_cases_path, "r", encoding="utf-8") as f:
    TEST_CASES = json.load(f)

@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", TEST_CASES, ids=[tc["id"] for tc in TEST_CASES])
async def test_llm_response_accuracy(test_case):
    """
    Test đánh giá chất lượng câu trả lời của LLM cho từng test case.
    """
    input_message = test_case["input_message"]
    cv_text = test_case.get("cv_text", "")
    expected_keywords = test_case.get("expected_keywords", [])
    negative_keywords = test_case.get("negative_keywords", [])

    print(f"\n[{test_case['id']}] Testing prompt: {input_message}".encode('utf-8', 'replace').decode('cp1252', 'ignore'))

    # Khởi tạo trạng thái ban đầu giả lập cho LangGraph
    initial_state = {
        "message": input_message,
        "cv_text": cv_text,
        "cv_hash": "dummy_hash",
        "history": [],
        "user_memory": "Người dùng đang trong phiên test tự động.",
        "session_summary": "",
        "knowledge": "",
        "graph_context": "", 
        "market_context": "",
        "internet_context": "", 
        "ai_data_json": "", 
        "draft_text": "", 
        "feedback": "", 
        "eval_pass": True, 
        "retry_count": 0, 
        "final_prompt": "",
        "system_prompt_ref": "", 
        "user_prompt_ref": ""
    }

    final_state = initial_state.copy()
    
    # Chạy LangGraph (Gọi LLM thật)
    async for output in app_graph.astream(initial_state):
        for node_name, state_update in output.items():
            final_state.update(state_update)

    # Lấy bản nháp cuối cùng
    ai_response = final_state.get("draft_text", "")
    ai_response_lower = ai_response.lower()

    print(f"\n🤖 AI Response:\n{ai_response.encode('utf-8', 'replace').decode('cp1252', 'ignore')}\n")

    # Đánh giá bằng Keyword Matching (Assert)
    if expected_keywords:
        matched = [kw for kw in expected_keywords if kw.lower() in ai_response_lower]
        assert len(matched) > 0, f"AI không chứa từ khóa mong đợi. Các từ kỳ vọng: {expected_keywords}. AI trả về: {ai_response}"

    if negative_keywords:
        matched_neg = [kw for kw in negative_keywords if kw.lower() in ai_response_lower]
        assert len(matched_neg) == 0, f"AI chứa từ khóa BỊ CẤM. Các từ dính: {matched_neg}. AI trả về: {ai_response}"
