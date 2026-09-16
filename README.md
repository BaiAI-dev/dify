# dify
# 韶音智能客服 Agent（Dify + FastAPI + Streamlit）

## 📖 项目简介
基于 Dify 云端工作流与自研 FastAPI 中间件构建的企业级智能客服系统。接入韶音真实产品手册，支持 RAG 检索与流式打字机输出。

## 🏗️ 架构设计
```mermaid
graph LR
    User[用户] --> Streamlit[Streamlit 前端界面]
    Streamlit -->|HTTP POST| FastAPI[FastAPI 中间件]
    FastAPI -->|API Key| Dify[Dify 云端工作流]
    Dify -->|RAG 检索| Knowledge[韶音产品手册知识库]
    Dify -->|LLM 推理| DeepSeek[DeepSeek 模型]

    真实 RAG 落地：基于韶音 OpenComm2 官方手册构建 Dify 知识库，实现了高质量切片、向量检索与 Rerank 重排。

自研中间件：手写 FastAPI 服务替代现成组件，实现与 Dify API 的无缝对接及 SSE 流式转发。

流式体验优化：前端实现打字机效果，并在流式链路中通过状态机精准剥离大模型的 <think> 思考标签，保证输出纯净。