import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import requests
import json
import os

# ================= 配置区域 =================
# 飞书应用凭证（从环境变量读取，保证安全）
APP_ID = os.environ.get("FEISHU_APP_ID")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET")

# Dify API 配置
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")

# ================= 全局缓存 =================
# 1. 去重缓存：防止飞书重复推送事件
processed_events = set()

# 2. 会话记忆：维护 "飞书用户ID -> Dify conversation_id" 的映射
user_conversations = {}

def handle_message(message_id: str, user_id: str, user_input: str):
    """处理用户消息：调用 Dify 并回复飞书"""
    if not DIFY_API_KEY:
        print("错误：DIFY_API_KEY 未设置")
        return

    print(f"收到提问: {user_input} (用户: {user_id})")
    
    # 从缓存里取出该用户的历史会话 ID（如果是新用户，就是空字符串）
    conversation_id = user_conversations.get(user_id, "")

    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": user_input,
        "response_mode": "blocking",
        "user": user_id,
        "conversation_id": conversation_id  # 关键：带上历史会话 ID
    }
    
    try:
        resp = requests.post(DIFY_API_URL, headers=headers, json=payload, timeout=30)
        data = resp.json()
        answer = data.get("answer", "抱歉，我暂时无法回答。")
        
        # 关键：保存 Dify 返回的新 conversation_id，用于下一轮对话
        new_conversation_id = data.get("conversation_id")
        if new_conversation_id:
            user_conversations[user_id] = new_conversation_id
            print(f"更新用户 {user_id} 的会话 ID: {new_conversation_id}")
        
        # 过滤 <think> 标签
        if "</think>" in answer:
            answer = answer.split("</think>")[-1].strip()
            
    except Exception as e:
        answer = f"请求 Dify 出错：{str(e)}"
        print(answer)

    # 回复飞书
    client = lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()
    request = ReplyMessageRequest.builder() \
        .message_id(message_id) \
        .request_body(ReplyMessageRequestBody.builder()
            .content(json.dumps({"text": answer}))
            .msg_type("text")
            .build()) \
        .build()
    
    response = client.im.v1.message.reply(request)
    if not response.success():
        print(f"飞书回复失败: {response.code} - {response.msg}")
    else:
        print("已成功回复飞书！")

def do_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """处理接收到的消息事件（含去重与用户识别）"""
    try:
        # 去重逻辑
        event_id = data.header.event_id if data.header else None
        if event_id:
            if event_id in processed_events:
                return
            processed_events.add(event_id)
            if len(processed_events) > 1000:
                processed_events.clear()

        # 解析消息内容与用户 ID
        content = json.loads(data.event.message.content)
        user_input = content.get("text", "")
        
        # 从发送者信息中提取 open_id 作为该用户的唯一标识
        sender_open_id = data.event.sender.sender_id.open_id
        
        if user_input:
            handle_message(data.event.message.message_id, sender_open_id, user_input)
            
    except Exception as e:
        print(f"解析飞书消息失败: {e}")

def main():
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(do_message_receive_v1) \
        .build()

    cli = lark.ws.Client(APP_ID, APP_SECRET, event_handler=event_handler, log_level=lark.LogLevel.INFO)
    print("飞书机器人已启动，等待消息中...")
    cli.start()

if __name__ == "__main__":
    main()