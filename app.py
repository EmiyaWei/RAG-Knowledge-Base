import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
from pypdf import PdfReader
from datetime import datetime

st.set_page_config(page_title="企业级 RAG 知识库", page_icon="📚", layout="wide")

load_dotenv()
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not MY_API_KEY:
    st.error("未找到 API Key！")
    st.stop()

client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

# ==========================================
# 侧边栏
# ==========================================
with st.sidebar:
    st.title("⚙️ 知识库管理")
    
    # 【升级点 1】允许上传多个文件
    uploaded_files = st.file_uploader("上传 TXT 或 PDF 文档 (可多选)", type=["txt", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("📥 解析并存入新文档"):
            with st.spinner("正在解析文档..."):
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
    
    # 【升级点 2】展示已有文档，并支持单独删除
    st.subheader("📂 当前已存文档")
    existing_data = collection.get()
    if existing_data and existing_data['metadatas']:
        # 提取所有唯一的文件名
        sources = list(set([meta["source"] for meta in existing_data['metadatas']]))
        for source in sources:
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.write(f"📄 {source}")
            with col2:
                if st.button("🗑️", key=f"del_{source}", help="删除此文档"):
                    # 根据元数据中的文件名删除该文档的所有切片
                    collection.delete(where={"source": source})
                    st.rerun()
    else:
        st.info("当前知识库为空。")
        
    st.divider()
    
    top_k = st.slider("检索段落数量 (Top-K)", min_value=1, max_value=5, value=3)
    if st.button("🧹 清空知识库和对话", use_container_width=True):
        chroma_client.delete_collection(name="my_knowledge_base")
        collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 主界面
# ==========================================
st.title("📚 企业级 RAG 智能知识库")
st.caption("基于 DeepSeek + ChromaDB（支持多文档管理 + 溯源 + Agent）")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 聊天输入
user_input = st.chat_input("请输入关于文档的问题...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        with st.spinner("AI 正在检索和思考..."):
            # 1. 检索
            query_text = user_input
            if len(st.session_state.messages) > 1:
                query_text = st.session_state.messages[-2]["content"] + " " + user_input
            
            # 检查知识库是否有内容
            if collection.count() == 0:
                context = "知识库为空。"
            else:
                results = collection.query(query_texts=[query_text], n_results=top_k)
                context = ""
                if results['documents'] and len(results['documents'][0]) > 0:
                    for i in range(len(results['documents'][0])):
                        doc = results['documents'][0][i]
                        meta = results['metadatas'][0][i]
                        context += f"[文件:{meta['source']} 第{meta['page']}页]: {doc}\n\n"
            
            system_prompt = {
                "role": "system", 
                "content": f"请根据上下文回答。如果未提及，请说“文档中未提及”。末尾必须标注来源（文件名及页码）。\n\n【上下文片段】：\n{context}"
            }
            
            # 2. 工具
            tools = [{
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "获取当前系统时间",
                    "parameters": {"type": "object", "properties": {}},
                },
            }]

            messages_for_ai = [system_prompt] + st.session_state.messages
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages_for_ai,
                tools=tools,
                tool_choice="auto",
                stream=False 
            )
            
            response_msg = response.choices[0].message
            messages_for_ai.append(response_msg)

            # 3. 处理工具
            if response_msg.tool_calls:
                for tool_call in response_msg.tool_calls:
                    if tool_call.function.name == "get_current_time":
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        messages_for_ai.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "get_current_time",
                            "content": current_time,
                        })
                
                final_response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages_for_ai,
                    stream=True
                )
                ai_reply = st.write_stream(final_response)
            else:
                final_response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages_for_ai,
                    stream=True
                )
                ai_reply = st.write_stream(final_response)
            
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
