from openai import OpenAI

# Khởi tạo client kết nối tới Colab của bạn
client = OpenAI(
    base_url="https://tenesha-utterable-karlyn.ngrok-free.dev/v1",
    api_key="ollama-boc-phet", # API key điền bừa gì cũng được vì Ollama không check
    default_headers={"ngrok-skip-browser-warning": "true"} # Vượt tường lửa Ngrok
)

print("Đang gửi tin nhắn cho Llama 3...")
response = client.chat.completions.create(
    model="my-llama3", # Đúng tên model bạn đã tạo ở Colab
    messages=[
        {"role": "system", "content": "Bạn là một trợ lý AI nói tiếng Việt xuất sắc."},
        {"role": "user", "content": "Xin chào, 1 cộng 1 bằng mấy? Trả lời ngắn gọn."}
    ],
    temperature=0.7
)

# In câu trả lời
print("\n🤖 Trả lời từ Llama 3:")
print(response.choices[0].message.content)