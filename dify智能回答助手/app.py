import streamlit as st
import requests

st.set_page_config(page_title="韶音智能客服", page_icon="🎧", layout="wide")
st.title("🎧 韶音智能客服 Agent 演示")
st.write("基于 Dify 知识库与 DeepSeek V4 模型，实时回答韶音产品问题。")

user_input = st.text_input("请输入您的问题（例如：OpenComm2怎么开机？）：", "OpenComm2怎么开机？")

if st.button("发送"):
    if user_input.strip():
        st.write("回答：")
        with st.spinner("正在检索知识库..."):
            try:
                # 调用 FastAPI 中间件获取流式响应
                res = requests.post(
                    "http://127.0.0.1:8000/webhook",
                    json={"user_input": user_input},
                    stream=True
                )
                
                placeholder = st.empty()
                final_answer = ""
                buffer = ""
                
                # 逐块处理流，彻底剥离 <think> 标签
                for chunk in res.iter_content(chunk_size=1, decode_unicode=True):
                    if not chunk:
                        continue
                    
                    buffer += chunk
                    
                    # 只要包含 </think>，说明思考结束，提取后面的干净内容
                    if "</think>" in buffer:
                        clean_part = buffer.split("</think>")[-1]
                        final_answer += clean_part
                        buffer = ""
                        placeholder.write(final_answer)
                    # 如果包含 <think>，说明还在思考，把前面的丢弃
                    elif "<think>" in buffer:
                        # 丢弃 <think> 之前的内容，保留 <think> 之后的内容
                        buffer = buffer.split("<think>")[-1]
                    # 如果既没有 <think> 也没有 </think>，且已经出现过思考结束标志，则正常输出
                    # （这段逻辑由上面 `</think>` 的判断分支覆盖）
                    elif not buffer.startswith("<") and "</think>" not in buffer and "思考" not in buffer:
                        # 这只是一个简单的后备逻辑，防止部分内容卡在标签中
                        pass

                # 如果全部过滤完还没有输出任何内容（比如模型没有产生思考），则直接输出最终的文本
                if final_answer and not placeholder.empty():
                    pass
                elif buffer:
                    placeholder.write(buffer)
                        
            except Exception as e:
                st.error(f"调用接口失败：{str(e)}")
    else:
        st.warning("请输入内容")