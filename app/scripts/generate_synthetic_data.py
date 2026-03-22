import json
import os
import asyncio
from typing import List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.core.llm import get_llm_vip
from app.core.logger import logger
from dotenv import load_dotenv
load_dotenv()
class Message(BaseModel):
    role: str = Field(description="Chỉ được chọn 'user' hoặc 'assistant'")
    content: str = Field(description="Nội dung câu hỏi của ứng viên hoặc câu trả lời của Tech Lead")

class Conversation(BaseModel):
    messages: List[Message] = Field(description="Một cuộc hội thoại hỏi-đáp hoàn chỉnh (gồm 1 câu user hỏi và 1 câu assistant đáp)")

class SyntheticData(BaseModel):
    conversations: List[Conversation] = Field(description="Danh sách các cuộc hội thoại được sinh ra")

SYSTEM_PROMPT = """Bạn là một Chuyên gia Nhân sự (HR) cấp cao kiêm Tech Lead tận tâm.
Nhiệm vụ của bạn là tư vấn CV, định hướng sự nghiệp và phỏng vấn kỹ thuật thuật toán (Live-Coding) một cách khắt khe nhưng mang tính xây dựng. 
Luôn trả lời súc tích, chuyên nghiệp và có chuyên môn sâu về IT."""
# MẢNG 100 KỊCH BẢN TRAINING SIÊU ĐA DẠNG (MỞ RỘNG)
SCENARIOS= [
# MẢNG 50 KỊCH BẢN TRAINING: ĐỤNG ĐỘ THỰC TẾ & KỶ NGUYÊN AI
    # --- NHÓM 1: CÚ ĐÊM OUTSOURCE & AGENCY (LÀM DỰ ÁN CHO KHÁCH) ---
    "Sale hứa với khách hàng làm app xịn như Grab trong vòng 1 tháng với giá 50 triệu. Sale kéo cả team IT vào phòng họp ép cam kết tiến độ. Tech Lead lật bàn.",
    "Khách hàng phi kỹ thuật (Non-tech) nằng nặc đòi dùng Blockchain để... lưu trữ ảnh sản phẩm trên web bán quần áo cho 'bảo mật'. PM giải thích sao cho khách hiểu?",
    "Khách hàng đã ký nghiệm thu giai đoạn 1, nhưng lại nhắn tin riêng lén lút nhờ Dev 'thêm vài nút nhỏ xíu anh nhờ tý' để né phí (Charge) của PM.",
    "Bàn giao Source Code xong, khách hàng tự đổi pass Server, chê code rác rồi giở trò không chịu thanh toán 50% số tiền còn lại. Công ty xử lý khủng hoảng.",
    "Khách nước ngoài bắt meeting lúc 1h sáng thứ Bảy hàng tuần để cập nhật tiến độ vì lệch múi giờ. PM đàm phán để bảo vệ sức khỏe và Work-life balance cho team.",
    "Dự án Fix-cost (giá cố định trọn gói) nhưng khách đổi Requirement liên tục 15 lần. PM đòi thu thêm tiền thì khách dọa bóc phốt lên các group IT. Xử lý truyền thông.",
    "Team nhận bảo trì một dự án do công ty khác (đã phá sản) để lại. Mở Source Code ra thấy toàn biến đặt tên tiếng Ấn Độ/Nhật Bản và không có 1 dòng Document nào. Tech Lead ra hướng giải quyết.",
    "Dự án đang làm dở thì khách hàng thông báo... hết ngân sách, xin khất nợ hoặc trả bằng 'cổ phần của dự án'. Giám đốc phải ra quyết định.",
    "App làm đúng y chang tài liệu thiết kế (Figma), nhưng khi ra mắt không ai dùng. Khách hàng quay ra đổ lỗi do team IT làm app trải nghiệm kém.",

    # --- NHÓM 2: ỨNG DỤNG AI & XU HƯỚNG CÔNG NGHỆ ---
    "Dev lạm dụng GitHub Copilot/ChatGPT sinh code nhưng không thèm đọc kỹ logic, đẩy thẳng lên Production gây sai số liệu tài chính của khách hàng.",
    "Sếp Tổng đọc báo thấy AI đang hot, yêu cầu đuổi việc đội Content/CSKH và bắt Tech Lead dùng 1 tuần build một con AI Chatbot thay thế hoàn toàn con người. Tech Lead đánh giá rủi ro.",
    "Ứng viên phỏng vấn vị trí AI Engineer chém gió tung trời, nhưng khi hỏi sâu vào bản chất toán học hoặc kiến trúc RAG (Retrieval-Augmented Generation) thì chỉ biết... gọi API của OpenAI.",
    "Dev dùng ChatGPT để nhờ tìm bug, nhưng vô tình copy/paste luôn cả đoạn code chứa API Key của đối tác và Password Database Production lên cửa sổ chat. Lỗ hổng rò rỉ dữ liệu.",
    "Sinh viên thực tập tự tin nói với Tech Lead: 'Anh không cần dạy em thuật toán đâu, AI giờ nó code thay hết rồi, em chỉ cần học Prompt là đủ'. Tech Lead chỉnh đốn tư duy.",
    "Công cụ quét AI phát hiện 80% bài test kỹ năng của ứng viên được sinh ra từ máy. HR hủy kết quả, ứng viên gân cổ cãi 'Đó là kỹ năng dùng tool của em'.",
    "Model AI của công ty tự động duyệt hồ sơ vay vốn nhưng lại thiên vị (Bias), từ chối toàn bộ khách hàng nữ. Data Scientist bị gọi lên phòng họp khẩn cấp.",

    # --- NHÓM 3: XUNG ĐỘT LIÊN PHÒNG BAN (CROSS-DEPARTMENTAL DRAMA) ---
    "Phòng Marketing chạy chiến dịch Livestream mời KOL tặng quà lúc 20h tối thứ Sáu nhưng... quên không báo team IT. Traffic tăng x100 lần, server sập ngay phút đầu tiên.",
    "Kế toán phàn nàn team IT dùng Cloud (AWS/Azure) tốn nhiều tiền vô lý (500 củ/tháng), ép hạ cấu hình Server xuống thấp nhất để tiết kiệm. DevOps phản bác bằng số liệu.",
    "Designer vẽ giao diện (UI) cực kỳ bay bổng với Animation 3D phức tạp, Frontend Dev kêu làm không được hoặc web sẽ lag tung chảo. Hai bên cãi nhau không ai nhường ai.",
    "App gặp lỗi thanh toán, team Customer Service (CSKH) tức giận chửi thẳng mặt team Dev là 'ăn hại' trên Group Chat chung của toàn công ty. Quản lý hai bên can thiệp.",
    "Bộ phận Pháp chế (Legal) yêu cầu mã hóa toàn bộ dữ liệu người dùng ngay trong đêm để tuân thủ luật bảo vệ dữ liệu (GDPR/PDP). Tech Lead giải thích nếu làm vậy app sẽ chậm đi 50%.",
    "Sales chốt được hợp đồng tỷ đô nhưng khách yêu cầu phải cài đặt hệ thống lên Server On-premise cực kỳ cũ kỹ (chạy Windows Server 2008) của họ. Cả phòng IT khóc thét.",

    # --- NHÓM 4: ONBOARDING & ĐÀO TẠO (MENTORSHIP) ---
    "Senior Dev cực giỏi nhưng 'giấu nghề', Fresher hỏi gì cũng ném cho cái link Google bắt tự đọc, thái độ hách dịch khiến Fresher nản nộp đơn nghỉ việc sau đúng 2 tuần.",
    "Thực tập sinh ngày đầu tiên đi làm, do không được phân quyền kỹ đã lỡ tay xóa nhầm nhánh (branch) 'main' trên Git. Kịch bản Tech Lead xử lý khủng hoảng và tâm lý cho bạn trẻ.",
    "Giao task cho Middle Dev, bạn này không biết làm nhưng giấu dốt không báo cáo. Đến sát giờ Release buổi chiều mới thản nhiên nói 'Em chưa làm gì cả'.",
    "Mentor giao bài tập cho thử việc nhưng không thèm Review Code hay Feedback. Cuối tháng HR dựa vào lời Mentor đánh giá 'không có sự tiến bộ' để đuổi ứng viên. HR điều tra ngược lại Mentor.",
    "Nhân viên IT Onboarding ngày đầu nhưng công ty thiếu thiết bị. Dev mới vào ngồi chơi xơi nước, lướt web suốt 1 tuần không có máy tính/account để làm việc. Bức xúc viết review 1 sao trên ITviec.",
    "Ứng viên tranh luận gay gắt với HR vì công ty bắt ép ký cam kết 'Nếu nghỉ việc trong vòng 1 năm kể từ lúc học việc phải đền bù chi phí đào tạo 50 triệu'.",
    "Công ty tuyển một nhân viên cũ quay lại làm việc (Boomerang Employee) nhưng lại trả mức lương cao hơn cả Leader hiện tại của team đó. Gây chia rẽ nội bộ sâu sắc.",

    # --- NHÓM 5: BẢO MẬT & THẢM HỌA AN TOÀN THÔNG TIN (CYBERSECURITY) ---
    "Nhân viên mượn USB của người ngoài cắm vào máy tính công ty để chép file tài liệu, vô tình lây nhiễm mã độc tống tiền (Ransomware) lây lan ra toàn mạng nội bộ.",
    "Phỏng vấn vòng CV: Ứng viên gửi email ứng tuyển nhưng file đính kèm là đuôi `.exe` hoặc file nén yêu cầu nhập pass lạ. Bộ phận IT nghi ngờ lừa đảo (Phishing) đánh cắp token.",
    "Đội kiểm toán hệ thống (Audit) phát hiện công ty vẫn đang lưu mật khẩu của 5 triệu người dùng dưới dạng Plain-text (chữ trần, không mã hóa) suốt 5 năm qua.",
    "Cựu nhân viên cay cú vì bị sa thải bất ngờ, dùng tài khoản cũ (do IT quên chưa khóa/Revoke) lén đăng nhập vào phá hoại data khách hàng.",
    "Công ty thương mại điện tử bị đối thủ dùng tool tự động cào (Crawl) sạch dữ liệu bảng giá cập nhật mỗi phút, làm cạn kiệt băng thông server. Kỹ sư tìm cách giăng bẫy chặn Bot.",
    "Developer dùng chung 1 password cho cả tài khoản Root của Server, GitHub công ty, và... tài khoản game cá nhân. Bị lộ pass game dẫn đến mất luôn quyền điều khiển hệ thống công ty.",
    "App chỉ là chức năng báo thức nhưng Dev lại code yêu cầu cấp quyền truy cập Danh bạ và Định vị GPS. Bị Apple/Google Store từ chối (Reject), Dev phải giải trình với PO."
]


async def generate_data():
    logger.info("ĐẺ DỮ LIỆU TỔNG HỢP (SYNTHETIC DATA)...")
    
    llm_generator = get_llm_vip().with_structured_output(SyntheticData)
    
    output_file = os.path.join(os.getcwd(), "dataset.jsonl")
    total_conversations = 0
    
    with open(output_file, 'a', encoding='utf-8') as f:
        
        for idx, scenario in enumerate(SCENARIOS):
            logger.info(f"Đang suy nghĩ Kịch bản {idx + 1}/{len(SCENARIOS)}: {scenario[:50]}...")
            
            prompt = f"""Hãy sinh ra 1 cuộc hội thoại (conversations) khác nhau dựa trên tình huống sau: '{scenario}'.
Mỗi cuộc hội thoại chỉ cần 8 lượt (4 lượt 'user' hỏi, 4 lượt 'assistant' trả lời).
Câu trả lời của 'assistant' phải thể hiện đúng phong cách của một Tech Lead chuyên nghiệp, gắt gao nhưng tận tâm."""
            
            try:
                result: SyntheticData = await llm_generator.ainvoke([HumanMessage(content=prompt)])
                
                for convo in result.conversations:
                    chat_data = {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT}
                        ]
                    }
                    for msg in convo.messages:
                        chat_data["messages"].append({"role": msg.role, "content": msg.content})
                    
                    f.write(json.dumps(chat_data, ensure_ascii=False) + '\n')
                    total_conversations += 1
                    
                logger.info(f"Đã sinh thành công 3 hội thoại cho Kịch bản {idx + 1}.")
                
            except Exception as e:
                logger.error(f"Lỗi ở Kịch bản {idx + 1}: {e}")
                
            await asyncio.sleep(6)

    logger.info(f"Đã đẻ thêm {total_conversations} cuộc hội thoại cực kỳ chất lượng vào {output_file}.")

if __name__ == "__main__":
    asyncio.run(generate_data())