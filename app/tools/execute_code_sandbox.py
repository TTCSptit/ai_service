import requests
from langchain_core.tools import tool

@tool
def execute_code_sandbox(language:str ,source_code:str,test_inputs:str)->str:
    """
    Công cụ chạy thử code của ứng viên (Sandbox Piston). Sử dụng công cụ này BẤT CỨ KHI NÀO ứng viên nộp một đoạn mã nguồn để trả lời cho Code Challenge.
    Tham số:
    - language: Ngôn ngữ lập trình (bắt buộc: python, javascript, hoặc java).
    - source_code: Toàn bộ đoạn mã nguồn hoàn chỉnh có thể biên dịch được.
    - test_inputs: Các thông số đầu vào qua stdin (nếu có yêu cầu nhập xuất, ngược lại để chuỗi rỗng "").
    """
    lang_map = {
        "python": "3.10.0",
        "javascript": "18.15.0",
        "java": "15.0.2"
    }
    version = lang_map.get(language.lower(),"3.10.0")

    payload = {
        "language": language.lower(),
        "version": version,
        "files": [{"content": source_code}],
        "stdin": test_inputs 
    }
    try:
        response = requests.post("https://emkc.org/api/v2/piston/execute", json=payload)
        result = response.json()

        if 'run' in result:
            output = result['run']['stdout']
            error = result['run']['stderr']
            if error:
                return f"Lỗi thực thi (Runtime Error):\n{error}"
            return f"Kết quả chạy (Output):\n{output}"
        else:
            return "Lỗi Server Sandbox: Không thể chạy code."
    except Exception as e:
        return f"Sandbox bị lỗi kết nối: {str(e)}"

CODETOOL = [execute_code_sandbox]