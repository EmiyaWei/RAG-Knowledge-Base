import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
from pypdf import PdfReader

st.set_page_config(page_title="企业级 RAG 知识库", page_icon="📚", layout="wide")

load_dotenv()
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not MY_API_KEY:
    st.error("未找到 API Key，请检查 .env 文件配置！")
    st.stop()

client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")

with st.sidebar:
    st.title("⚙️ 控制面板")
    st.markdown("在这里上传文档并设置参数。")
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
st.caption("基于 DeepSeek + ChromaDB 构建的检索增强生成系统（支持来源溯源）")

# 删掉那个 @st.cache_resource 的函数，直接暴力持久化
chroma_client = chromadb.PersistentClient(path="./chroma_db")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if uploaded_file is not None:
    if "file_name" not in st.session_state or st.session_state.file_name != uploaded_file.name:
        with st.spinner("正在解析文档并存入向量数据库..."):
            documents = []
            metadatas = []
            ids = []
            
            # 【改造点 1：带上页码信息】
            if uploaded_file.name.endswith(".pdf"):
                pdf_reader = PdfReader(uploaded_file)
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    text = page.extract_text()
                    if text:
                        # 按页切分
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
            
            try:
                chroma_client.delete_collection(name="my_knowledge_base")
            except:
                pass
                
            collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            st.session_state.file_name = uploaded_file.name
            st.session_state.file_processed = True 
            
        st.success(f"✅ `{uploaded_file.name}` 已成功存入大脑！")
    else:
        collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

    user_input = st.chat_input("请输入关于文档的问题...")
    
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("assistant"):
            with st.spinner("AI 正在检索和思考..."):
                query_text = user_input
                if len(st.session_state.messages) > 1:
                    query_text = st.session_state.messages[-2]["content"] + " " + user_input
                
                results = collection.query(query_texts=[query_text], n_results=top_k)
                
                # 【改造点 2：把页码和内容拼在一起给 AI 看】
                context = ""
                for i in range(len(results['documents'][0])):
                    doc = results['documents'][0][i]
                    meta = results['metadatas'][0][i]
                    context += f"[第{meta['page']}页]: {doc}\n\n"
                
                # 【改造点 3：强制要求 AI 引用页码】
                system_prompt = {
                    "role": "system", 
                    "content": f"请根据以下提供的上下文片段回答问题。如果上下文中没有答案，请直接说“文档中未提及”。\n"
                               f"⚠️非常重要：在你的回答末尾，必须用括号标注你参考的页码，例如：（参考来源：第2页）。\n\n【上下文片段】：\n{context}"
                }
                messages_for_ai = [system_prompt] + st.session_state.messages
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages_for_ai,
                    stream=True
                )
                
                ai_reply = st.write_stream(response)
                
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
