import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from database import get_chroma_client, process_and_store_files
from tools import get_current_time, search_knowledge_base, search_internet, get_weather, TOOLS_SCHEMA

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
        # 温和且清晰的提示词
        system_prompt = {
    "role": "system", 
    "content": (
        "你是一个智能助手。请根据用户的意图，使用相应的工具。\n"
        "1. 如果用户问文档内容，使用 search_knowledge_base。\n"
        "⚠️【检索核心指令】：\n"
        "（1）传入的 query 必须是精炼的关键词。\n"
        "（2）如果你发现查出来的内容与你问的问题无关，请立刻改变关键词再查一次。\n"
        # 👇 核心杀手锏：必须按指定格式输出
        "（3）如果你调用了工具并查到了内容，你在最终回复时，**必须直接以冒号开头并列出条款（如：一、考试时间：... 二、报名资格：...）**，绝对禁止使用“以上就是”、“已为您列出”这种敷衍的词语！如果查不到，直接说“未提及”。\n"
        "2. 如果用户问天气，使用 get_weather。\n"
        "3. 如果用户问时间，使用 get_current_time。\n"
        "4. ⚠️严禁输出任何 `<|DSML|>` 标签！"
    )
}
        
        messages_for_ai = [system_prompt] + st.session_state.messages
        
        with st.status("🧠 AI 正在思考并调度工具...", expanded=True) as status:
            for i in range(3):
                response = client.chat.completions.create(
                    model="deepseek-chat", messages=messages_for_ai, tools=TOOLS_SCHEMA, tool_choice="auto"
                )
                response_msg = response.choices[0].message
                messages_for_ai.append(response_msg)

                if response_msg.tool_calls:
                    for tool_call in response_msg.tool_calls:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        
                        st.write(f"🔍 调用工具：`{func_name}`，参数：`{args}`")
                        
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
                        
                        # 👇 教练帮你加上了透视镜，你想看后台抓了啥就点开
                        with st.expander(f"👀 查看 {func_name} 的返回结果"):
                            st.info(result)
                            
                        messages_for_ai.append({
                            "tool_call_id": tool_call.id, "role": "tool", "name": func_name, "content": result
                        })
                else:
                    break
            
            status.update(label="✅ 工具调用完成！", state="complete", expanded=False)

        # 最终流式输出
        final_response = client.chat.completions.create(model="deepseek-chat", messages=messages_for_ai, stream=True)
        ai_reply = st.write_stream(final_response)
        
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
