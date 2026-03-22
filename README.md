---
title: AI Career Advisor
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# AI Career Advisor API Backend 🚀

Dự án cung cấp một hệ thống Backend API tiên tiến ứng dụng Trí tuệ Nhân tạo để đóng vai trò như một Chuyên gia Nhân sự (HR) và Tech Lead, hỗ trợ ứng viên đánh giá CV và rèn luyện phỏng vấn (Mock Interview). Hệ thống được thiết kế theo kiến trúc Micro-services, cung cấp luồng dữ liệu thời gian thực (Streaming) và tích hợp các công nghệ RAG mạnh mẽ.

## ✨ Chức Năng Nổi Bật

1. **Tư Vấn & Phân Tích CV Tự Động (AI CV Analyzer):**
   - Đọc và trích xuất thông tin định dạng PDF của ứng viên thông qua `pdfplumber`.
   - Phân tích ưu/nhược điểm trong CV, chấm điểm độ phù hợp (Matching Score) và trả về định dạng JSON chuẩn.
   - Nhận diện các kỹ năng (Skills) đã có, những kỹ năng đang thiếu sót, từ đó đưa ra lời khuyên thiết thực để nâng cấp hồ sơ.

2. **Mô Phỏng Phỏng Vấn Kỹ Thuật (Mock Interview):**
   - Đóng vai nguyên mẫu một *Tech Lead cực kỳ khắt khe*.
   - Khả năng đọc ngữ cảnh thông minh: Tự động kích hoạt khi người dùng muốn được phỏng vấn.
   - Trực tiếp hỏi các câu hỏi hóc búa liên quan đến các công nghệ trong CV. Chờ đợi câu trả lời, nhận xét đúng/sai và đưa ra giải pháp "Best Practice".

3. **Cơ Chế RAG & Tìm Kiếm Internet Thông Minh:**
   - **RAG (Retrieval-Augmented Generation)**: Chứa một cơ sở dữ liệu `Vector Database` (thông qua ChromaDB). Tự động nạp kiến thức chuyên môn nội bộ từ các file văn bản (`.txt`) ở thư mục `data/` vào cơ sở dữ liệu để đưa ra tư vấn.
   - **Router Agent**: Trang bị công cụ tìm kiếm `DuckDuckGoSearchRun` phân tích thời gian thực xem câu hỏi của người dùng có cần cào dữ liệu mới nhất trên mạng hay không.

4. **Multi-Agent & Hệ Thống Đánh Giá (AI Evaluator):**
   - Trước khi gửi câu trả lời về cho ứng viên, hệ thống sẽ sinh ra một "Bản nháp".
   - Bản nháp này sẽ được "Tech Lead AI" đọc và phản biện. Sau khi đạt thỏa thuận về độ khó, chuẩn xác của kiến thức, kết quả cuối cùng hoàn hảo nhất mới được sinh ra.
   
5. **Real-time Streaming & Quản Lý Sessions:**
   - Hỗ trợ server-sent events (SSE) qua FastAPI StreamingResponse, mang lại trải nghiệm chat mượt mà, tốc độ cao.
   - Chat history được lưu an toàn với CSDL PostgreSQL (Sử dụng `SQLAlchemy`) thông qua định danh `session_id` để chatbot ghi nhớ lịch sử hội thoại.

---

## 🛠 Công Nghệ Sử Dụng

- **Framework**: `FastAPI`, `Uvicorn`
- **AI / LLMs**: `Google Gemini` (thông qua `LangChain`), `Groq`
- **Cơ Sở Dữ Liệu**: `PostgreSQL` (Quản lý chat history), `ChromaDB` (Vector Database lưu trữ RAG).
- **Embeddings**: `sentence-transformers` (model: `all-MiniLM-L6-v2`)
- **Khác**: `pdfplumber` (xử lý PDF), `Pydantic` (Data Validation).

---

## 🚀 Hướng Dẫn Cài Đặt (Local Development)

### 1. Yêu cầu hệ thống:
- `Python 3.10+`
- Có sẵn kết nối PostgreSQL.

### 2. Các bước triển khai:

**Bước 1:** Clone repository về máy:
```bash
git clone <repository_url>
cd ai_service
```

**Bước 2:** Tạo môi trường ảo và cài đặt các thư viện:
```bash
python -m venv venv
# Trên Windows:
.\venv\Scripts\activate
# Trên Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

**Bước 3:** Cấu hình biến môi trường:
Tạo file `.env` tại thư mục gốc của dự án với nội dung như sau:
```env
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://user:password@host:port/database_name?sslmode=require
```

**Bước 4:** Nạp tài liệu Knowledge Base cho RAG:
Bỏ các hướng dẫn, tài liệu chuyên môn của bạn dưới dạng **.txt** vào thư mục `data/`. Hệ thống sẽ tự động vector hóa và nạp vào ChromaDB ở lần khởi động đầu tiên.

**Bước 5:** Khởi chạy Server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API của bạn sẽ hoạt động hoàn hảo tại `http://localhost:8000`.

---

## 🐳 Hướng Dẫn Triển Khai bằng Docker

Dự án đã có sẵn `Dockerfile` chuẩn hóa để triển khai trên bất kỳ server nào hoặc trực tiếp lên Hugging Face Spaces.

**Build Docker Image:**
```bash
docker build -t ai-career-advisor .
```

**Run Container:**
Chú ý expose cổng `7860` để tương thích với cấu hình hiện tại trong Dockerfile.
```bash
docker run -p 7860:7860 --env-file .env ai-career-advisor
```

---

## 📖 Cấu Trúc Thư Mục

```text
ai_service/
├── app/                  # Chứa toàn bộ logic ứng dụng
│   ├── api/              # Các route API xử lý (vd: chat.py)
│   ├── core/             # Cấu hình thiết lập (DB init, LLMs setup, settings)
│   ├── schemas/          # Các class Pydantic định dạng dữ liệu (payload/response)
│   ├── services/         # Dịch vụ riêng phân nhánh logic (RAG, CV Parser)
│   └── main.py           # Entry point khởi chạy app FastAPI
├── data/                 # Thư mục bỏ các tệp tin .txt cho hệ thống AI học (RAG)
├── vector_db/            # (Tự sinh) Thư mục được ChromaDB tạo ra lưu trữ vector Embeddings
├── test/                 # Các tệp kịch bản kiểm thử API
├── .env                  # Chứa các biến môi trường
├── Dockerfile            # Cấu hình cài đặt môi trường Container
├── requirements.txt      # Tổng hợp các danh sách thư viện python
└── README.md             # File hướng dẫn
```
