from fastapi import FastAPI
import requests
import os

app = FastAPI()

# 明天在终端设置环境变量：export DIFY_API_KEY="你的key"
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"

@app.post("/webhook")
async def dify_proxy(user_input: str):
    """把用户输入转发给 Dify，并返回回答"""
    if not DIFY_API_KEY:
        return {"error": "API Key 未配置"}
        
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": user_input,
        "response_mode": "blocking",
        "user": "test_user"
    }
    
    try:
        response = requests.post(DIFY_API_URL, headers=headers, json=payload)
        return {"reply": response.json().get("answer", "解析错误")}
    except Exception as e:
        return {"error": str(e)}