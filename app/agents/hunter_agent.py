import asyncio
from langchain_core.messages import HumanMessage
from langchain_community.tools import DuckDuckGoSearchResults
from app.core.llm import get_llm_cheap
from app.core.logger import logger
from langsmith import traceable

class CareerHunterAgent:
    def __init__(self):
        self.search_tool = DuckDuckGoSearchResults()

    @traceable(run_type="chain", name="Hunt Jobs via CV")
    async def execute(self, cv_text: str) -> str:
        logger.info("[Hunter Agent] Bắt đầu phân tích CV để tìm việc...")
        try:
            # Bước 1: Phân tích CV và lấy ra 2-3 chức danh công việc phù hợp nhất
            extract_prompt = f"""Dưới đây là nội dung CV của ứng viên:
{cv_text[:5000]}  # Giới hạn 5000 ký tự để tiết kiệm context

Nhiệm vụ: Dựa vào kinh nghiệm và kỹ năng trong CV này, hãy gợi ý 1 CỤM TỪ TÌM KIẾM NGẮN GỌN (tối đa 5-6 từ) bằng tiếng Việt hoặc tiếng Anh để tìm kiếm tin tuyển dụng phù hợp nhất.
Ví dụ: "Tuyển dụng Backend Developer Nodejs" hoặc "Tuyển dụng Data Analyst SQL".
CHỈ TRẢ VỀ CỤM TỪ TÌM KIẾM, KHÔNG GIẢI THÍCH."""

            query_response = await get_llm_cheap().ainvoke([HumanMessage(content=extract_prompt)])
            search_query = query_response.content.strip().replace('"', '')
            logger.info(f"[Hunter Agent] Search Query: {search_query}")

            # Bước 2: Cào việc làm trên mạng
            logger.info(f"[Hunter Agent] Đang cào dữ liệu cho: {search_query}...")
            search_results = await asyncio.to_thread(self.search_tool.run, search_query)

            if not search_results or len(search_results.strip()) < 50:
                logger.warning("[Hunter Agent] Không tìm thấy kết quả từ DuckDuckGo.")
                return "<p>Hiện tại chúng tôi chưa tìm thấy công việc mới nào hoàn toàn khớp với CV của bạn trên Internet. Hãy tiếp tục nâng cao kỹ năng nhé!</p>"

            # Bước 3: Định dạng kết quả thành Email HTML
            format_prompt = f"""Dưới đây là các kết quả tìm việc cho "{search_query}":
{search_results}

Nhiệm vụ: Hãy đóng vai AI Career Advisor. Hãy viết một đoạn mã HTML sinh động (chỉ dùng thẻ <div>, <ul>, <li>, <strong>, <a>, <br>).
Nội dung: 
- Chào ứng viên, thông báo vừa phân tích CV của họ xong.
- Liệt kê 2-3 cơ hội việc làm tốt nhất từ dữ liệu trên. 
- YÊU CẦU BẮT BUỘC: Bạn PHẢI bóc tách đường link (URL) từ dữ liệu cung cấp và đặt vào thẻ <a href="Đường_link_ở_đây" target="_blank">Xem chi tiết công việc</a> để người dùng có thể bấm vào được. Không được tự bịa ra link giả.
- Viết thân thiện, chuyên nghiệp, khích lệ. 
TUYỆT ĐỐI CHỈ TRẢ VỀ MÃ HTML (KHÔNG CẦN THẺ <html> HAY <body>), KHÔNG CÓ MARKDOWN BLOCK HAY LỜI BÌNH."""

            email_content_response = await get_llm_cheap().ainvoke([HumanMessage(content=format_prompt)])
            email_html = email_content_response.content.strip()
            
            # Xóa các markdown blocks nếu có
            if email_html.startswith("```html"):
                email_html = email_html.replace("```html", "").replace("```", "").strip()
            elif email_html.startswith("```"):
                email_html = email_html.replace("```", "").strip()

            logger.info("[Hunter Agent] Đã soạn xong nội dung Email.")
            return email_html

        except Exception as e:
            logger.error(f"[Hunter Agent Lỗi]: {e}", exc_info=True)
            return "<p>Xin lỗi, quá trình săn việc tự động đang gặp sự cố. Chúng tôi sẽ thử lại sau.</p>"
