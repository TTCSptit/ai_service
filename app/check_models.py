from app.core.llm import get_llm_kaggle_v1, get_llm_kaggle_v2
from langchain_core.messages import SystemMessage, HumanMessage

def test_kaggle_backups():
    print("🚀 Đang kiểm tra các model backup từ Kaggle...\n")
    
    # 1. Kiểm tra Backup 1 (Ngrok)
    print("🔹 Đang gọi Llama 3 (Ngrok - Backup 1)...")
    try:
        llm1 = get_llm_kaggle_v1()
        messages1 = [
            SystemMessage(content="Bạn là một trợ lý AI thông minh. Hãy trả lời ngắn gọn, súc tích bằng tiếng Việt."),
            HumanMessage(content="WebRTC là gì?")
        ]
        response1 = llm1.invoke(messages1)
        print("🤖 Llama 3 (Ngrok) trả lời:")
        print("-" * 50)
        print(response1.content)
        print("-" * 50)
    except Exception as e:
        print(f"❌ Lỗi khi gọi Backup 1: {e}")

    print("\n" + "="*60 + "\n")

    # 2. Kiểm tra Backup 2 (Pinggy)
    print("🔹 Đang gọi Llama 3 (Pinggy - Backup 2)...")
    try:
        llm2 = get_llm_kaggle_v2()
        messages2 = [
            SystemMessage(content="Bạn là chuyên gia về đồ án tốt nghiệp IT."),
            HumanMessage(content="Chào bạn, hãy cho tôi biết ưu điểm lớn nhất của hệ thống Multi-Agent là gì?")
        ]
        response2 = llm2.invoke(messages2)
        print("🤖 Llama 3 (Pinggy) trả lời:")
        print("-" * 50)
        print(response2.content)
        print("-" * 50)
    except Exception as e:
        print(f"❌ Lỗi khi gọi Backup 2: {e}")

if __name__ == "__main__":
    test_kaggle_backups()
