import os
from groq import Groq

client = Groq(api_key="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")

res = client.chat.completions.create(
    model="mixtral-8x7b",
    messages=[{"role": "user", "content": "hi"}]
)

print(res)