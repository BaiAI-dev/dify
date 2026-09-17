import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import requests
import json
import os

# ================= 配置区域 =================
# 1. 飞书应用凭证（请确认已替换为你自己的）
APP_ID = "FEISHU_APP_ID"
APP_SECRET = "FEISHU_APP_SECRET"

# 2. Dify API 配置
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")

# ================= 全局缓存：防止飞书事件重复推送 =================
# 飞书采用“至少一次”推送策略，网络抖动时会重发相同的事件
processed_events = set()

def handle_message(message_id: str, user_input: str):
    """处理用户消息：调用 Dify 并回复飞书"""
    if not DIFY_API_KEY:
        print("错误：DIFY_API_KEY 未设置，请在终端执行 export DIFY_API_KEY='app-xxx'")
        return

    print(f"收到提问: {user_input}")
    
    # 1. 调用 Dify API
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": user_input,
        "response_mode": "blocking", # 飞书这里用阻塞模式，获取完整回答
        "user": "feishu_user"
    }
    
    try:
        resp = requests.post(DIFY_API_URL, headers=headers, json=payload, timeout=30)
        answer = resp.json().get("answer", "抱歉，我暂时无法回答。")
        
        # 关键：过滤掉 DeepSeek V4 可能产生的 <think> 思考标签
        if "</think>" in answer:
            answer = answer.split("</think>")[-1].strip()
            
    except Exception as e:
        answer = f"请求 Dify 出错：{str(e)}"
        print(answer)

    # 2. 回复飞书消息
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
    """处理接收到的消息事件（含去重机制）"""
    try:
        # 提取飞书事件的唯一ID进行去重
        event_id = data.header.event_id if data.header else None
        
        if event_id:
            if event_id in processed_events:
                print(f"忽略重复事件: {event_id}")
                return
            processed_events.add(event_id)
            
            # 限制集合大小，防止内存无限增长（保留最近1000个事件ID）
            if len(processed_events) > 1000:
                processed_events.clear()

        # 解析飞书消息内容
        content = json.loads(data.event.message.content)
        user_input = content.get("text", "")
        if user_input:
            handle_message(data.event.message.message_id, user_input)
            
    except Exception as e:
        print(f"解析飞书消息失败: {e}")

def main():
    # 注册事件处理器（长连接模式）
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(do_message_receive_v1) \
        .build()

    # 启动 WebSocket 客户端
    cli = lark.ws.Client(APP_ID, APP_SECRET, event_handler=event_handler, log_level=lark.LogLevel.INFO)
    print("飞书机器人已启动，等待消息中...")
    cli.start()

if __name__ == "__main__":
    main()