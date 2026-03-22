import os

# 1. Khai báo thư mục chứa data
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 2. Nội dung 20 file tri thức cho AI
knowledge_base = {
    # --- NHÓM 1: LỘ TRÌNH HỌC TẬP (ROADMAP) ---
    "roadmap_frontend.txt": "Lộ trình Frontend Developer: Bắt buộc nắm vững HTML, CSS, JavaScript cơ bản. Sau đó học sâu về ReactJS hoặc VueJS. Cần biết sử dụng Git, hiểu về RESTful API và quản lý state (Redux/Zustand). Kỹ năng cộng thêm: TypeScript và tiếng Anh giao tiếp.",
    "roadmap_backend_nestjs.txt": "Lộ trình Backend Node.js (NestJS): Yêu cầu bắt buộc là TypeScript và kiến trúc OOP. Cần thành thạo framework NestJS, biết cách tích hợp ORM như Prisma hoặc TypeORM. Bắt buộc hiểu về cơ sở dữ liệu quan hệ (PostgreSQL/MySQL) và cách thiết kế API bảo mật (JWT).",
    "roadmap_backend_python.txt": "Lộ trình Backend Python: Nắm vững Python Core, cấu trúc dữ liệu. Học framework FastAPI hoặc Django. Cần biết cách viết test (pytest), làm việc với Docker và hiểu cơ bản về kiến trúc Microservices. Tiếng Anh đọc hiểu tài liệu là bắt buộc.",
    "roadmap_ai_engineer.txt": "Lộ trình AI Engineer: Bắt buộc giỏi Toán (Đại số tuyến tính, Xác suất thống kê) và Python. Thành thạo các thư viện: Pandas, NumPy, Scikit-learn. Làm quen với Deep Learning qua PyTorch hoặc TensorFlow. Cần biết về Vector Database (ChromaDB, FAISS) và Prompt Engineering.",
    "roadmap_mobile_flutter.txt": "Lộ trình Mobile Developer (Flutter): Nắm vững ngôn ngữ Dart. Hiểu sâu về Widget tree và State Management (Provider, Bloc, GetX). Biết cách gọi API, làm việc với Firebase và quy trình đẩy app lên App Store/Google Play.",
    "roadmap_devops.txt": "Lộ trình DevOps Engineer: Bắt buộc thành thạo Linux căn bản và Shell Script. Hiểu sâu về Containerization (Docker, Kubernetes). Biết thiết lập CI/CD pipeline (GitHub Actions, Jenkins) và làm quen với Cloud Services (AWS hoặc Google Cloud).",
    "roadmap_qa_tester.txt": "Lộ trình QA/QC Tester: Nắm vững quy trình kiểm thử phần mềm. Bắt đầu với Manual Test (viết Test Case, báo cáo Bug). Nâng cao bằng Automation Test sử dụng Selenium, Cypress hoặc Playwright. Biết test API qua Postman.",
    "roadmap_data_analyst.txt": "Lộ trình Data Analyst (DA): Kỹ năng sinh tồn là SQL và Excel nâng cao. Biết sử dụng công cụ trực quan hóa dữ liệu (PowerBI, Tableau). Khuyến khích học thêm Python hoặc R để xử lý dữ liệu lớn.",
    
    # --- NHÓM 2: MÔ TẢ CÔNG VIỆC (JD) TẠI CÁC CÔNG TY ---
    "jd_fresher_react.txt": "Tuyển dụng Fresher ReactJS tại PTIT Tech: Yêu cầu sinh viên mới ra trường hoặc dưới 1 năm kinh nghiệm. Nắm chắc HTML/CSS/JS, đã có project cá nhân làm bằng ReactJS. Lương khởi điểm: 8 - 12 triệu VNĐ. Môi trường trẻ trung, không yêu cầu kinh nghiệm thực tế.",
    "jd_junior_python.txt": "Tuyển dụng Junior Python Backend: Yêu cầu từ 1 năm kinh nghiệm làm việc với FastAPI hoặc Django. Có kinh nghiệm thao tác với Database. Ưu tiên ứng viên biết dùng Git và Docker cơ bản. Mức lương: 15 - 20 triệu VNĐ.",
    "jd_middle_nestjs.txt": "Tuyển Middle Backend NestJS: Yêu cầu 2-3 năm kinh nghiệm. Thành thạo TypeScript, NestJS, Prisma và PostgreSQL. Có khả năng tối ưu query và viết Unit Test. Lương: 20 - 30 triệu VNĐ + Thưởng dự án.",
    "jd_senior_ai.txt": "Tuyển Senior AI/ML Engineer: Yêu cầu 3+ năm kinh nghiệm xử lý ngôn ngữ tự nhiên (NLP) hoặc thị giác máy tính (CV). Đã từng deploy model lên production. Tiếng Anh giao tiếp tốt. Lương: Cạnh tranh (từ $2000 trở lên).",
    "jd_intern_tester.txt": "Tuyển Thực tập sinh Tester (QA/QC): Chấp nhận sinh viên năm 3, năm 4. Được đào tạo quy trình test chuẩn Agile. Yêu cầu chăm chỉ, cẩn thận, tư duy logic tốt. Có phụ cấp thực tập 3-5 triệu/tháng và cơ hội lên nhân viên chính thức.",
    "jd_uiux_designer.txt": "Tuyển UI/UX Designer: Yêu cầu 1 năm kinh nghiệm. Thành thạo Figma. Có tư duy thẩm mỹ tốt, hiểu về trải nghiệm người dùng trên Mobile và Web. Yêu cầu gửi kèm Portfolio (Behance/Dribbble) khi ứng tuyển. Lương: 12 - 18 triệu.",
    
    # --- NHÓM 3: TƯ VẤN NHÂN SỰ & KỸ NĂNG (HR TIPS) ---
    "hr_cv_ats_format.txt": "Cách viết CV chuẩn ATS: Các hệ thống lọc CV tự động (ATS) không đọc được định dạng quá cầu kỳ. Hãy dùng font chữ cơ bản, thiết kế 1 cột. Không dùng biểu đồ cột/tròn để đánh giá kỹ năng. Lưu file dưới định dạng PDF có thể bôi đen chữ được.",
    "hr_cv_star_method.txt": "Phương pháp STAR khi viết CV: Thay vì ghi 'Làm backend cho web', hãy viết theo chuẩn STAR (Situation-Task-Action-Result): 'Phát triển API bằng NestJS và Prisma, tối ưu hóa truy vấn giúp giảm 30% thời gian tải trang'. Những con số cụ thể sẽ thu hút nhà tuyển dụng.",
    "hr_interview_soft_skills.txt": "Kỹ năng mềm khi phỏng vấn: Nhà tuyển dụng đánh giá cao thái độ hơn trình độ. Hãy thể hiện sự cầu thị, trung thực (nếu không biết hãy nhận là chưa tìm hiểu sâu, tuyệt đối không bịa đặt). Luôn chuẩn bị trước 1-2 câu hỏi để hỏi lại nhà tuyển dụng vào cuối buổi.",
    "hr_salary_negotiation.txt": "Kỹ năng deal lương: Trước khi phỏng vấn, hãy tham khảo mức lương thị trường cho số năm kinh nghiệm của mình. Khi được hỏi mức lương mong muốn, hãy đưa ra một 'khoảng' (ví dụ: 15-18 triệu) thay vì một con số cố định, và nhấn mạnh rằng có thể linh hoạt theo chế độ đãi ngộ.",
    "hr_english_importance.txt": "Tầm quan trọng của Tiếng Anh trong ngành IT: Nếu chỉ biết tiếng Việt, mức lương của bạn thường sẽ chạm trần ở mức Middle. Để tiến lên Senior hoặc làm ở các công ty Outsource/Global, tiếng Anh giao tiếp là điều kiện tiên quyết. Tối thiểu phải đọc hiểu được tài liệu tiếng Anh.",
    "hr_career_switch.txt": "Tư vấn chuyển ngành sang IT: Nếu bạn học trái ngành, hãy bắt đầu bằng việc tự học qua các khóa học ngắn hạn hoặc Bootcamp. Hãy làm thật nhiều dự án cá nhân (Pet Projects) và đưa lên GitHub. CV của người chuyển ngành cần tập trung vào các dự án thực tế để bù đắp cho việc thiếu bằng cấp IT.",
    # --- KINH TẾ / KINH DOANH ---
    "roadmap_marketing.txt" : "Lộ trình Digital Marketing: Yêu cầu khả năng phân tích tâm lý khách hàng. Cần nắm vững SEO, chạy Ads (Facebook/Google), và Content Marketing. Kỹ năng nâng cao: Sử dụng Google Analytics, Data Studio để đọc chỉ số. Lương Fresher khoảng 8-10 triệu.",
    "roadmap_ke_toan.txt": "Lộ trình Kế toán/Kiểm toán: Bắt buộc nắm chắc Luật Kế toán, Thuế doanh nghiệp. Thành thạo Excel và phần mềm kế toán (MISA, FAST). Lộ trình thăng tiến: Kế toán viên -> Kế toán tổng hợp -> Kế toán trưởng. Ưu tiên có chứng chỉ ACCA hoặc CPA.",
    "roadmap_sales_b2b.txt": "Lộ trình Sales B2B (Doanh nghiệp bán cho Doanh nghiệp): Yêu cầu kỹ năng giao tiếp xuất sắc, kiên nhẫn. Biết cách quản lý khách hàng qua phần mềm CRM (Salesforce, Hubspot). Thu nhập chủ yếu đến từ hoa hồng (Commission).",
    
    # --- THIẾT KẾ / SÁNG TẠO ---
    "roadmap_graphic_design.txt": "Lộ trình Graphic Designer: Nắm vững bộ công cụ Adobe (Photoshop, Illustrator, InDesign). Hiểu biết về bố cục, màu sắc, Typography. Bắt buộc phải có Portfolio (Behance) khi đi xin việc. Môi trường làm việc thường là các Agency quảng cáo.",
    
    # --- NHÂN SỰ / HÀNH CHÍNH ---
    "roadmap_hr_admin.txt": "Lộ trình chuyên viên Nhân sự (HR): Chia làm 2 mảng chính là Tuyển dụng (TA) và Lương thưởng (C&B). Cần am hiểu Luật Lao động, BHXH. Kỹ năng giao tiếp và xử lý tình huống khéo léo là bắt buộc.",
    
    # --- Y TẾ / CHĂM SÓC SỨC KHỎE ---
    "roadmap_dieu_duong.txt": "Lộ trình Điều dưỡng viên: Bắt buộc tốt nghiệp chuyên ngành Điều dưỡng. Yêu cầu sự cẩn thận, y đức, và khả năng chịu áp lực cao trực ca đêm. Cơ hội tu nghiệp và làm việc tại Đức, Nhật Bản với mức lương rất cao."
    
}

# 3. Vòng lặp tự động tạo 20 file
print("🚀 Đang khởi tạo bộ dữ liệu tri thức AI...")
for filename, content in knowledge_base.items():
    file_path = os.path.join(DATA_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        print(f"✔️ Đã tạo file: {filename}")

print("\n🎉 HOÀN TẤT! Đã tạo xong 20 file tri thức vào thư mục 'data'.")