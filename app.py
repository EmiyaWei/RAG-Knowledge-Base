import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv
from pypdf import PdfReader

# 页面基础配置（必须放在最前面）
st.set_page_config(page_title="企业级 RAG 知识库", page_icon="📚", layout="wide")

load_dotenv()
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not MY_API_KEY:
    st.error("未找到 API Key，请检查 .env 文件配置！")
    st.stop()

client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")

# ==========================================
# 1. 侧边栏设计 (Sidebar)
# ==========================================
with st.sidebar:
    st.title("⚙️ 控制面板")
    st.markdown("在这里上传文档并设置参数。")
    
    # 将上传组件移到侧边栏
    uploaded_file = st.file_uploader("请上传 TXT 或 PDF 文档", type=["txt", "pdf"])
    
    # 加一个滑动条，让用户自己决定检索几段内容（Top-K）
    top_k = st.slider("检索段落数量 (Top-K)", min_value=1, max_value=5, value=3)
    
    st.divider() # 画一条分割线
      # 清空对话按钮
    if st.button("🗑️ 清空当前对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.file_processed = False
        if "file_name" in st.session_state:
            del st.session_state.file_name
        st.rerun() # 强制刷新页面

# ==========================================
# 2. 主界面设计 (Main)
# ==========================================
st.title("📚 企业级 RAG 智能知识库")
st.caption("基于 DeepSeek + ChromaDB 构建的检索增强生成系统")

@st.cache_resource
def get_chroma_client():
    return chromadb.Client()

chroma_client = get_chroma_client()

if "messages" not in st.session_state:
    st.session_state.messages = []

# 展示历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 处理文件上传与向量化
if uploaded_file is not None:
    if "file_name" not in st.session_state or st.session_state.file_name != uploaded_file.name:
        with st.spinner("正在解析文档并存入向量数据库..."):
            file_content = ""
            if uploaded_file.name.endswith(".pdf"):
                pdf_reader = PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        file_content += text + "\n"
            else:
                file_content = uploaded_file.read().decode("utf-8")
            
            try:
                chroma_client.delete_collection(name="my_knowledge_base")
            except:
                pass
                
            chunk_size = 500
            chunks = [file_content[i:i+chunk_size] for i in range(0, len(file_content), chunk_size)]
            collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
            collection.add(
                documents=chunks, 
                ids=[str(i) for i in range(len(chunks))] 
            )
            
            st.session_state.file_name = uploaded_file.name
            st.session_state.file_processed = True 
            
        st.success(f"✅ `{uploaded_file.name}` 已成功存入大脑！可以开始提问了。")
    else:
        collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

    # 聊天输入框
    user_input = st.chat_input("请输入关于文档的问题...")
    
    if user_input:
        # 显示用户提问
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # AI 回答
        with st.chat_message("assistant"):
            with st.spinner("AI 正在检索和思考..."):
                query_text = user_input
                if len(st.session_state.messages) > 1:
                    query_text = st.session_state.messages[-2]["content"] + " " + user_input
                
                # 使用侧边栏设置的值 top_k
                results = collection.query(query_texts=[query_text], n_results=top_k)
                context = "\n\n".join(results['documents'][0])
                
                system_prompt = {
                    "role": "system", 
                    "content": f"请严格根据以下提供的上下文片段，回答用户的问题。如果上下文中没有答案，请直接说“文档中未提及”。\n\n【上下文片段】：\n{context}"
                }
                messages_for_ai = [system_prompt] + st.session_state.messages
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages_for_ai,
                    stream=True
                )
                
                ai_reply = st.write_stream(response)
                
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})

else:
    # 如果还没上传文件，主界面给点提示
    st.info("👈 请先在左侧控制面板上传一份 PDF 或 TXT 文件。")
