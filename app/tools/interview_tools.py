import os
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from e2b_code_interpreter import Sandbox
from app.core.llm import get_llm_cheap
from app.core.logger import logger
from app.core.config import settings
os.environ["E2B_API_KEY"] = settings.E2B

@tool
def analyze_candidate_code(code:str,problem_description:str)->str:
    """
    Sub-Agent chuyên trách chấm thi. Sử dụng công cụ này BẤT CỨ KHI NÀO ứng viên nộp một đoạn code.
    Tham số:
    - code: Đoạn mã nguồn ứng viên viết.
    - problem_description: Tóm tắt bài toán ứng viên đang giải (Ví dụ: "Viết hàm tính Fibonacci").
    """
    logger.info("[Sub-Agent] Khởi động môi trường Sandbox chấm thi...")
    execution_result =""
    try:
        with Sandbox() as sandbox:
            execution = sandbox.run_code(code)

            if execution.error:
                execution_result = f"[LỖI BIÊN DỊCH/RUNTIME]: {execution.error.name} - {execution.error.value}"
            else:
                execution_result = f"[KẾT QUẢ CHẠY THÀNH CÔNG]:\n{execution.text}"
    except Exception as e:
        return f"Hệ thống Sandbox đang bảo trì: {e}"
    logger.info("[Sub-Agent] Đang phân tích độ phức tạp Time/Space và Clean Code...")
    
    analysis_prompt = f"""Bạn là chuyên gia thuật toán.
        Bài toán: {problem_description}
        Code của ứng viên:
        ```python
        {code}
        Kết quả trên Sandbox: {execution_result}

        Hãy trả về Báo Cáo Chấm Thi siêu ngắn gọn:

        Trạng thái: (Thành công/Thất bại).

        Độ phức tạp thời gian (Big-O).

        Độ phức tạp không gian.

        Clean Code: (Biến, Comment, SOLID).

        Gợi ý tối ưu.
        """
    try:
        report_res = get_llm_cheap().invoke([HumanMessage(content=analysis_prompt)])
        logger.info("[Sub-Agent] Đã hoàn tất báo cáo chấm thi!")
        return report_res.content
    except Exception as e:
        return f"Kết quả chạy: {execution_result}\n(Lỗi tạo báo cáo: {e})"
INTERVIEW_TOOLS = [analyze_candidate_code]