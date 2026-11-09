🤖 企业级 RAG 智能 Agent 系统 (Enterprise AI Agent)
基于 DeepSeek + ChromaDB + FastAPI 打造的全栈 AI 智能体应用。

核心亮点：

· 🧠 Agent 智能路由：支持多工具（Function Calling）自主调度（天气、时间、本地文档）。
· 🔍 混合检索防幻觉：结合向量语义与 $contains 关键词强匹配，解决长文档检索语义混淆。通过 Prompt 强制约束并附带页码溯源。
· ⚡ 前后端分离架构：前端基于 Streamlit，后端使用 FastAPI 提供 SSE 流式（Streaming）接口，实现打字机输出效果。
· 🗄️ SQLite 持久化：本地数据库完美记忆多轮对话历史，告别刷新失忆。

技术栈：Python, FastAPI, Streamlit, ChromaDB, SQLite, pdfplumber, DeepSeek API.
