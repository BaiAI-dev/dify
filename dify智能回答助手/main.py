from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import requests
import os
import json

app = FastAPI()

DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"

@app.post("/webhook")
async def dify_proxy(request: Request):
    data = await request.json()
    user_input = data.get("user_input", "")
    
    if not DIFY_API_KEY:
        return {"error": "API Key 未配置"}

    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": user_input,
        "response_mode": "streaming", # 改为流式
        "user": "test_user"
    }

    def event_stream():
        response = requests.post(DIFY_API_URL, headers=headers, json=payload, stream=True)
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]
                    try:
                        data = json.loads(json_str)
                        if "answer" in data:
                            yield data["answer"]
                    except:
                        pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")