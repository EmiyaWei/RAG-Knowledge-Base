import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from database import get_chroma_client, process_and_store_files
from tools import get_current_time, search_knowledge_base, search_internet

st.set_page_config(page_title="Agent RAG 知识库", page_icon="🤖", layout="wide")
load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

@st.cache_resource
def init_chroma():
    return get_chroma_client()

chroma_client = init_chroma()

with st.sidebar:
    st.title("⚙️ 知识库管理")
    uploaded_files = st.file_uploader("上传 TXT 或 PDF 文档 (可多选)", type=["txt", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("📥 解析并存入新文档"):
            with st.spinner("正在解析文档..."):
                process_and_store_files(chroma_client, uploaded_files)
                st.success("✅ 文档已全部存入大脑！")
    
    st.divider()
    if st.button("🧹 清空知识库和对话", use_container_width=True):
        try:
            chroma_client.delete_collection(name="my_knowledge_base")
        except Exception:
            pass
        st.session_state.messages = []
        st.rerun()

st.title("🤖 模块化 Agent 智能路由")
st.caption("支持本地文档检索 + 联网搜索 + 实时时间")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("输入问题，看看 AI 会用什么工具...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        with st.spinner("AI 正在思考并调度工具..."):
            
            tools = [
    {
        "type": "function", 
        "function": {
            "name": "get_current_time", 
            "description": "获取当前的系统时间", 
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "search_knowledge_base", 
            "description": "查找本地上传的私有文档（如PDF、TXT）里的内容。当用户问及他们上传的文件、资料、考试时间、具体规定时，必须使用此工具。", 
            "parameters": {
                "type": "object", 
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                }, 
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "search_internet", 
            "description": "当用户询问今天发生的新闻、实时天气、或非私有文档的通用实时信息时，使用此工具进行联网搜索。", 
            "parameters": {
                "type": "object", 
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                }, 
                "required": ["query"]
            }
        }
    }
]

            system_prompt = {
                "role": "system", 
                "content": (
                    "你是一个智能路由助手。你必须遵守以下规则：\n"
                    "1. 当用户询问文档内容（如考试时间、条款、规定）时，必须优先使用 `search_knowledge_base`。\n"
                    "2. 当用户询问今天新闻、实时天气时，使用 `search_internet`。\n"
                    "3. 当用户询问现在几点时，使用 `get_current_time`。\n"
                    "如果工具返回错误或失败，请立刻停止调用该工具，直接用你的通用知识回答，严禁死循环重试！\n"
                    "⚠️严禁输出任何类似 <|DSML|> 的乱码标签！"
                )
            }
            
            # 这里是修复缩进的关键，请确保前面是 12 个空格
            messages_for_ai = [system_prompt] + st.session_state.messages
            
            for i in range(3):
                response = client.chat.completions.create(
                    model="deepseek-chat", messages=messages_for_ai, tools=tools, tool_choice="auto"
                )
                response_msg = response.choices[0].message
                messages_for_ai.append(response_msg)

                if response_msg.tool_calls:
                    for tool_call in response_msg.tool_calls:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        st.write(f"🛠️ *AI 决定调用工具：`{func_name}`*")
                        
                        if func_name == "get_current_time":
                            result = get_current_time()
                        elif func_name == "search_knowledge_base":
                            result = search_knowledge_base(chroma_client, args.get("query", ""))
                        elif func_name == "search_internet":
                            result = search_internet(args.get("query", ""))
                        else:
                            result = "未知工具"
                            
                        messages_for_ai.append({
                            "tool_call_id": tool_call.id, "role": "tool", "name": func_name, "content": result
                        })
                else:
                    break
            
            final_response = client.chat.completions.create(model="deepseek-chat", messages=messages_for_ai, stream=True)
            ai_reply = st.write_stream(final_response)
            
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
