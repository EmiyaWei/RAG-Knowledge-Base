import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from database import get_chroma_client, process_and_store_files
# 👇 导入你的超级机器人
from agent_class import MyAgent 

st.set_page_config(page_title="Agent RAG 知识库", page_icon="🤖", layout="wide")
load_dotenv()

# ==========================================
# 1. 初始化机器人与仓库
# ==========================================
@st.cache_resource
def init_chroma():
    return get_chroma_client()

chroma_client = init_chroma()

if "my_agent" not in st.session_state:
    st.session_state.my_agent = MyAgent(name="曹江韦的网页机器人")
    
agent = st.session_state.my_agent

# ==========================================
# 2. 左侧边栏：知识库管理
# ==========================================
with st.sidebar:
    st.title("大肥鱼的超级AI人民共和国")
    uploaded_files = st.file_uploader("上传 TXT 或 PDF 文档 (可多选)", type=["txt", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("📥 解析并存入新文档"):
            with st.spinner("正在解析文档..."):
                process_and_store_files(agent.chroma_client, uploaded_files)
                st.success("✅ 文档已存入大脑！")
                st.rerun() 
    
    st.divider()
    
    if st.button("🧹 清空所有文档和对话", use_container_width=True):
        try:
            agent.chroma_client.delete_collection(name="my_knowledge_base")
        except Exception:
            pass
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 3. 主界面：聊天
# ==========================================
st.title("🤖 模块化 Agent 智能路由 (流式版)")
st.caption("底层使用面向对象封装的 MyAgent，支持打字机输出")

# 渲染历史聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

user_input = st.chat_input("输入问题，看看 AI 会用什么工具...")

# 👇👇👇 【第二步修改的地方就在这下面！】 👇👇👇
if user_input:
    # 1. 显示用户的气泡
    with st.chat_message("user"):
        st.markdown(user_input)
    # 存入网页的记忆
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 2. 显示 AI 的气泡
    with st.chat_message("assistant"):
        with st.spinner("AI 正在翻阅记忆并调度工具..."):
            
            # 💥 核心变化：用 st.write_stream 接住流式数据！
            # 这里的 agent.stream_run 就是你刚刚在 agent_class.py 里加的那个带 yield 的方法
            ai_reply = st.write_stream(agent.stream_run(user_input))
            
    # 3. 把完整的回答存入网页的记忆
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
