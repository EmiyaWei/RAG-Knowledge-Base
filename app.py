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

with st.sidebar:
    st.title("⚙️ 控制面板")
    uploaded_file = st.file_uploader("请上传 TXT 或 PDF 文档", type=["txt", "pdf"])
    top_k = st.slider("检索段落数量 (Top-K)", min_value=1, max_value=5, value=3)
    st.divider() 
    if st.button("🗑️ 清空当前对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.file_processed = False
        if "file_name" in st.session_state:
            del st.session_state.file_name
        st.rerun()

st.title("📚 企业级 RAG 智能知识库")
st.caption("基于 DeepSeek + ChromaDB 构建（支持溯源 + Agent工具）")

# 初始化硬盘数据库
chroma_client = chromadb.PersistentClient(path="./chroma_db")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if uploaded_file is not None:
    # 如果上传了新文件，才去解析和存入
    if "file_name" not in st.session_state or st.session_state.file_name != uploaded_file.name:
        with st.spinner("正在解析文档..."):
            documents = []
            metadatas = []
            ids = []
            
            if uploaded_file.name.endswith(".pdf"):
                pdf_reader = PdfReader(uploaded_file)
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    text = page.extract_text()
                    if text:
                        chunks = [text[i:i+500] for i in range(0, len(text), 500)]
                        for chunk in chunks:
                            documents.append(chunk)
                            metadatas.append({"source": uploaded_file.name, "page": page_num})
                            ids.append(str(len(ids)))
            else:
                file_content = uploaded_file.read().decode("utf-8")
                chunks = [file_content[i:i+500] for i in range(0, len(file_content), 500)]
                for chunk in chunks:
                    documents.append(chunk)
                    metadatas.append({"source": uploaded_file.name, "page": "TXT全文"})
                    ids.append(str(len(ids)))
            
            # 安全地清理旧集合
            try:
                chroma_client.delete_collection(name="my_knowledge_base")
            except:
                pass
                
            # 【这里是之前报错漏掉的核心】先创建集合，再添加数据
            collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            
            st.session_state.file_name = uploaded_file.name
            st.session_state.file_processed = True 
        st.success(f"✅ `{uploaded_file.name}` 已成功存入！")
    
    # 【重要修复】不管是不是新文件，进入聊天前必须重新获取一次 collection 变量
    collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

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
                
                results = collection.query(query_texts=[query_text], n_results=top_k)
                context = ""
                # 加个防错判断，确保检索到了东西
                if results['documents'] and len(results['documents'][0]) > 0:
                    for i in range(len(results['documents'][0])):
                        doc = results['documents'][0][i]
                        meta = results['metadatas'][0][i]
                        context += f"[第{meta['page']}页]: {doc}\n\n"
                
                system_prompt = {
                    "role": "system", 
                    "content": f"请根据上下文回答用户。如果没有答案，请直接说“未提及”。末尾必须标注参考页码。\n\n【上下文片段】：\n{context}"
                }
                
                # 2. 工具准备
                tools = [{
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "description": "获取当前的系统时间",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }]

                messages_for_ai = [system_prompt] + st.session_state.messages
                
                # 3. 第一次请求
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages_for_ai,
                    tools=tools,
                    tool_choice="auto",
                    stream=False 
                )
                
                response_msg = response.choices[0].message
                messages_for_ai.append(response_msg)

                # 4. 工具处理
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
