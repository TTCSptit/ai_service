from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from app.core.llm import get_llm_cheap_v1, get_llm_vip
from app.prompts.system_prompts import get_evaluator_prompt
from app.core.logger import logger

from app.tools.interview_tools import INTERVIEW_TOOLS
from app.tools.execute_code_sandbox import execute_code_sandbox
from app.tools.github_tools import analyze_github_profile

COMBINED_TOOLS = INTERVIEW_TOOLS + [execute_code_sandbox, analyze_github_profile]

class EvaluationResult(BaseModel):
    is_pass: bool = Field(description="Đánh giá xem bản nháp có đạt yêu cầu không (True/False)")
    feedback: str = Field(description="Góp ý chi tiết để HR sửa lại bản nháp")

class TechLeadEvaluator:
    async def generate_draft(self, history, system_prompt: str, user_prompt: str) -> str:
        llm_with_tools = get_llm_cheap_v1().bind_tools(COMBINED_TOOLS)
        tool_check_messages = history + [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt + "\n\n(LƯU Ý QUAN TRỌNG: 1. NẾU ứng viên gửi code giải bài toán, BẮT BUỘC dùng lệnh sandbox để chạy. 2. NẾU ứng viên gửi file Github hoặc đưa Link Github, thiết bị BẮT BUỘC phải dùng `analyze_github_profile` để fetch codebase trước khi Review!)")
        ]
        
        tool_context = ""
        try:
            logger.info("[Agent Groq] Đang kiểm tra xem có cần gọi Sandbox không...")
            ai_msg = await llm_with_tools.ainvoke(tool_check_messages)
            
            if ai_msg.tool_calls:
                tool_check_messages.append(ai_msg)
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    logger.info(f"[Agent Groq] Dùng Tool: {tool_name}")
                    selected_tool = next(t for t in COMBINED_TOOLS if t.name == tool_name)
                    tool_output = selected_tool.invoke(tool_args)
                    tool_check_messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
                    
                    if tool_name == "analyze_github_profile":
                        tool_context += f"\n\n[DỮ LIỆU TỪ GITHUB]\n{tool_output}\n\nYÊU CẦU ĐẶC BIỆT DÀNH CHO TECH LEAD: Dựa vào mã nguồn vừa tải về này, HÃY XÍCH BƯỚC KHỎI LÍ THUYẾT VÀ REVIEW trực tiếp một điểm LỖI hoặc MỘT FILE CỤ THỂ. Không được nhận xét chung chung kiểu 'code sạch / cần cải thiện'."
                    else:
                        tool_context += f"\n\n[KẾT QUẢ CHẠY CODE SANDBOX]\n{tool_output}"
                
                logger.info("[Agent Groq] Đã có báo cáo từ hệ thống Tool.")

        except Exception as e:
            logger.warning(f"[Tool check lỗi, bỏ qua]: {e}")

        try:
            logger.info("[Agent LoRA] Đang sinh bản nháp với văn phong Tech Lead...")
            final_user_prompt = user_prompt + (tool_context if tool_context else "")
            messages = history + [
                SystemMessage(content=system_prompt),
                HumanMessage(content=final_user_prompt)
            ]
            final_draft = await get_llm_cheap_v1().ainvoke(messages)
            return final_draft.content
        except Exception as e:
            logger.error(f"Lỗi khi model  sinh bản nháp: {e}", exc_info=True)
            return "Xin lỗi, hệ thống tạo bản nháp đang gặp sự cố."

    async def evaluate(self, message: str, draft_text: str) -> tuple[bool, str]:
        prompt = get_evaluator_prompt(message, draft_text)
        try:
            structured_llm = get_llm_vip().with_structured_output(EvaluationResult)
            result: EvaluationResult = await structured_llm.ainvoke([HumanMessage(content=prompt)])
            return result.is_pass, result.feedback
        except Exception as e:
            logger.error(f"[Evaluator Lỗi]: {e}", exc_info=True)
            return True, "Lỗi chấm điểm, tự động duyệt."

    async def revise_draft(self, history, system_prompt: str, user_prompt: str, old_draft: str, feedback: str) -> str:
        revision_prompt = f"{system_prompt}\nTech Lead chê bản nháp cũ: {feedback}\nBản nháp cũ: {old_draft}\nHãy viết lại bản nháp tốt hơn."
        messages = history + [SystemMessage(content=revision_prompt), HumanMessage(content=user_prompt)]
        try:
            revised_res = await get_llm_cheap_v1().ainvoke(messages)
            return revised_res.content
        except Exception:
            return old_draft
            
    async def get_perfected_draft(self, history, system_prompt: str, user_prompt: str, message: str, max_retries: int = 2) -> tuple[str, str]:
        draft_text = await self.generate_draft(history, system_prompt, user_prompt)
        for attempt in range(max_retries):
            logger.info(f"[Agentic Loop] Giám khảo chấm điểm lần {attempt + 1}...")
            is_pass, feedback = await self.evaluate(message, draft_text)

            if is_pass:
                logger.info(f"[Giám khảo]: Pass=True | Feedback: {feedback} (Tuyệt vời, duyệt!)")
                return draft_text, "Bản nháp đã đạt chuẩn kỹ thuật."
                
            logger.warning(f"[Giám khảo]: Pass=False | Feedback: {feedback} (Yêu cầu làm lại!)")
            draft_text = await self.revise_draft(history, system_prompt, user_prompt, draft_text, feedback)
        
        logger.warning(f"Đã hết {max_retries} lượt sửa. Chấp nhận bản nháp hiện tại.")
        return draft_text, "Hãy lưu ý kỹ: " + feedback