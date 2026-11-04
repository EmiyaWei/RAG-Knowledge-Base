import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
# 👇 这里就是你需要找的 from tools import，一定要确保引入了 get_weather
from database import get_chroma_client, process_and_store_files
from tools import get_current_time, search_knowledge_base, search_internet, get_weather

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
st.caption("支持本地文档检索 + 真实天气查询 + 实时时间")

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
            
            # 定义所有可用的工具
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
                        "description": "当用户询问今天发生的新闻、或非私有文档的通用实时信息时，使用此工具进行联网搜索。", 
                        "parameters": {
                            "type": "object", 
                            "properties": {
                                "query": {"type": "string", "description": "搜索关键词"}
                            }, 
                            "required": ["query"]
                        }
                    }
                },
                # 👇 新增的天气工具
                {
                    "type": "function", 
                    "function": {
                        "name": "get_weather", 
                        "description": "查询某个城市的实时天气。当用户问今天天气怎么样、下不下雨时使用此工具。", 
                        "parameters": {
                            "type": "object", 
                            "properties": {
                                "city": {"type": "string", "description": "城市名称，例如：杭州、北京"}
                            }, 
                            "required": ["city"]
                        }
                    }
                }
            ]

            # 强化提示词，让 AI 优先使用真实天气接口
            system_prompt = {
                "role": "system", 
                "content": (
                    "你是一个智能路由助手。你必须遵守以下规则：\n"
                    "1. 当用户询问文档内容时，必须使用 `search_knowledge_base`。\n"
                    "2. 当用户明确问“天气怎么样”时，必须使用 `get_weather` 工具。\n"
                    "3. 当用户询问现在几点时，使用 `get_current_time`。\n"
                    "4. 只有当你需要查找最新新闻时，才使用 `search_internet`。\n"
                    "如果工具返回错误，请立刻停止，用通用知识回答，严禁死循环重试！"
                )
            }
            
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
                        elif func_name == "get_weather":
                            result = get_weather(args.get("city", "杭州"))
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
