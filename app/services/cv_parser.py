import pdfplumber
import io
from fastapi import UploadFile, HTTPException


from langsmith import traceable

@traceable(run_type="tool", name="Parse CV File")
async def extract_text_from_cv(file: UploadFile) -> str:
    """
    Hàm đọc và trích xuất văn bản từ file PDF tải lên.
    Trả về chuỗi văn bản (text) đã được làm sạch.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hệ thống chỉ hỗ trợ file PDF.")

    text_content = ""
    try:
        file_bytes = await file.read()
        pdf_stream = io.BytesIO(file_bytes)

        with pdfplumber.open(pdf_stream) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"

        cleaned_text = text_content.strip()
        if not cleaned_text:
            raise ValueError(
                "Không tìm thấy chữ trong CV (có thể đây là file ảnh scan)."
            )

        return cleaned_text

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc CV: {str(e)}")
