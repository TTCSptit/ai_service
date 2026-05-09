from openai import OpenAI

client = OpenAI(
    # ⚠️ QUAN TRỌNG: Phải có /v1 ở cuối đường link
    base_url="https://tenesha-utterable-karlyn.ngrok-free.dev/v1", 
    api_key="sk-no-key-required" 
)

print("🚀 Đang gửi câu hỏi lên Kaggle, chờ vài giây nhé...\n")

# 2. Gọi model trả lời
try:
    response = client.chat.completions.create(
      model="my-llama3", # Tên model bạn đã build ở Kaggle
      messages=[
        {"role": "system", "content": "Bạn là một trợ lý AI thông minh. Hãy trả lời ngắn gọn, súc tích bằng tiếng Việt."},
        {"role": "user", "content": "Giải thích cho tôi Agentic Workflow là gì trong 3 câu?"}
      ],
      temperature=0.7
    )

    print("🤖 Llama 3 (từ Kaggle) trả lời:")
    print("-" * 50)
    print(response.choices[0].message.content)
    print("-" * 50)

except Exception as e:
    print(f"❌ Có lỗi xảy ra: {e}")