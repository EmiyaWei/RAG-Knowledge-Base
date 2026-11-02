import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
from pypdf import PdfReader
from datetime import datetime
import json

st.set_page_config(page_title="Agent RAG 知识库", page_icon="🤖", layout="wide")

load_dotenv()
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not MY_API_KEY:
    st.error("未找到 API Key！")
    st.stop()

client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")

# 【云端适配】使用 EphemeralClient（内存模式）防止云端写入报错
chroma_client = chromadb.EphemeralClient()

# ==========================================
# 定义 AI 可以调用的“工具函数”
# ==========================================
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def search_knowledge_base(query: str):
    try:
        collection = chroma_client.get_collection(name="my_knowledge_base")
        if collection.count() == 0:
            return "知识库为空，请先在左侧上传文档。"
        
        results = collection.query(query_texts=[query], n_results=3)
        context = ""
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                context += f"[来源: {meta['source']} 第{meta['page']}页]: {doc}\n\n"
        return context if context else "未找到相关内容。"
    except Exception:
        return "知识库为空或检索失败。"

# ==========================================
# 侧边栏
# ==========================================
with st.sidebar:
    st.title("⚙️ 知识库管理")
    uploaded_files = st.file_uploader("上传 TXT 或 PDF 文档 (可多选)", type=["txt", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("📥 解析并存入新文档"):
            with st.spinner("正在解析文档..."):
                collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
                for file in uploaded_files:
                    documents, metadatas, ids = [], [], []
                    if file.name.endswith(".pdf"):
                        pdf_reader = PdfReader(file)
                        for page_num, page in enumerate(pdf_reader.pages, start=1):
                            text = page.extract_text()
                            if text:
                                chunks = [text[i:i+500] for i in range(0, len(text), 500)]
                                for chunk in chunks:
                                    documents.append(chunk)
                                    metadatas.append({"source": file.name, "page": page_num})
                                    ids.append(f"{file.name}_p{page_num}_{len(ids)}")
                    else:
                        text = file.read().decode("utf-8")
                        chunks = [text[i:i+500] for i in range(0, len(text), 500)]
                        for chunk in chunks:
                            documents.append(chunk)
                            metadatas.append({"source": file.name, "page": "TXT"})
                            ids.append(f"{file.name}_txt_{len(ids)}")
                    
                    if documents:
                        collection.add(documents=documents, metadatas=metadatas, ids=ids)
                st.success("✅ 文档已全部存入大脑！")
    
    st.divider()
    
    # 安全地展示已有文档
    try:
        collection = chroma_client.get_collection(name="my_knowledge_base")
        existing_data = collection.get()
        if existing_data and existing_data['metadatas']:
            sources = list(set([meta["source"] for meta in existing_data['metadatas']]))
            st.subheader("📂 当前已存文档")
            for source in sources:
                st.write(f"📄 {source}")
    except Exception:
        pass 
        
    st.divider()
    
    # 【修复】安全清空按钮，加了 try-except，再也不会报错了
    if st.button("🧹 清空知识库和对话", use_container_width=True):
        try:
            chroma_client.delete_collection(name="my_knowledge_base")
        except Exception:
            pass # 如果本来就没东西，就偷偷跳过，不报错
            
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 主界面与 Agent 循环
# ==========================================
st.title("🤖 Agent 智能路由知识库")
st.caption("支持多文档管理 + 自动思考调用工具 + 溯源")

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
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_knowledge_base",
                        "description": "当用户询问文档、文件里的相关内容等私有数据时，使用此工具去知识库检索",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "搜索的关键词或问题"}
                            },
                            "required": ["query"]
                        },
                    },
                }
            ]

            system_prompt = {
                "role": "system", 
                "content": "你是一个智能助手。你可以获取当前时间，也可以查询本地知识库。请根据用户的问题，自主决定调用哪个工具。如果调用了知识库，请在最终回答末尾附带来源。"
            }

            messages_for_ai = [system_prompt] + st.session_state.messages
            
            max_iterations = 3
            for i in range(max_iterations):
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages_for_ai,
                    tools=tools,
                    tool_choice="auto",
                )
                
                response_msg = response.choices[0].message
                messages_for_ai.append(response_msg)

                if response_msg.tool_calls:
                    for tool_call in response_msg.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        st.write(f"🛠️ *AI 决定调用工具：`{function_name}`*")
                        
                        if function_name == "get_current_time":
                            result = get_current_time()
                        elif function_name == "search_knowledge_base":
                            result = search_knowledge_base(function_args.get("query", ""))
                        else:
                            result = "未知工具"
                            
                        messages_for_ai.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": result,
                        })
                else:
                    break
            
            final_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages_for_ai,
                stream=True
            )
            ai_reply = st.write_stream(final_response)
            
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
