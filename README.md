# 🤖 企业级 RAG 智能 Agent 知识库系统

这是一个基于大模型、支持多工具智能路由、具备流式输出的全栈 AI Web 应用。前端采用 Streamlit，后端基于 FastAPI 构建 RESTful API，底层结合 ChromaDB 向量数据库实现检索增强生成（RAG）。

## ✨ 核心功能与技术亮点

*   **📄 复杂文档解析与 RAG 检索**：使用 `pdfplumber` 解析 PDF，结合自定义的重叠切片策略（Overlap Chunking）保证语义完整。引入**混合检索（Hybrid Search）**，通过 `$contains` 关键词强匹配解决向量检索“语义混淆”痛点，大幅提升召回率。
*   **🧠 Agent 多工具智能路由**：基于 DeepSeek API 的 Function Calling 能力，实现大模型自主规划。支持根据用户意图，自主调度「本地文档检索」、「真实天气查询」、「系统时间」等工具。
*   **🔍 防幻觉与强约束**：通过 System Prompt 强制要求模型提取 Query 关键词，并限制输出格式，确保大模型仅根据检索到的上下文作答，并在回答末尾附带来源页码。
*   **⚡ 前后端分离与流式输出**：前端仅负责 UI 渲染，后端 FastAPI 接口利用 `StreamingResponse` 实现 SSE（Server-Sent Events）流式打字机效果，极大降低用户等待焦虑。
*   **🗄️ 持久化存储**：基于 ChromaDB 实现多文档的独立管理与持久化存储，支持文件的独立增删查。

## 🛠️ 技术栈
*   **前端**：Streamlit (流式响应接收与渲染)
*   **后端**：FastAPI, Uvicorn
*   **大模型**：DeepSeek API (兼容 OpenAI SDK)
*   **向量数据库**：ChromaDB
*   **核心库**：pdfplumber, pypdf, python-dotenv

## 🚀 本地运行指南
1. 克隆本项目并进入目录。
2. 安装依赖：`pip install -r requirements.txt`
3. 在根目录创建 `.env` 文件，填入：`DEEPSEEK_API_KEY=你的Key`
4. 启动后端服务：`uvicorn main:app --reload`
5. 启动前端页面：`streamlit run app.py`
