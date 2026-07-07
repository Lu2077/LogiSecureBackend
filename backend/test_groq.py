import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    print("❌ No GROQ_API_KEY found!")
    exit()

print("✅ Groq API Key found!")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "llama-3.1-8b-instant",  # Super fast!
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 20
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("✅ SUCCESS!")
    print(response.json()["choices"][0]["message"]["content"])
else:
    print("❌ Error:", response.status_code)
    print(response.text)