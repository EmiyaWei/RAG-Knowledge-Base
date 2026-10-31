import streamlit as st
from openai import OpenAI
import chromadb
import os
from dotenv import load_dotenv

load_dotenv()
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not MY_API_KEY:
    st.error("未找到 API Key，请检查 .env 文件配置！")
    st.stop()

client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")

st.title("📚 企业级 RAG 智能知识库")
st.write("上传长文档，AI 精准检索相关段落后回答！")

uploaded_file = st.file_uploader("请上传一个 txt 文件", type=["txt"])

@st.cache_resource
def get_chroma_client():
    return chromadb.Client()

chroma_client = get_chroma_client()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if uploaded_file is not None:
    if "file_processed" not in st.session_state:
        with st.spinner("正在把文件切片并存入向量数据库..."):
            file_content = uploaded_file.read().decode("utf-8")
            chunk_size = 500
            chunks = [file_content[i:i+chunk_size] for i in range(0, len(file_content), chunk_size)]
            collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
            collection.add(
                documents=chunks, 
                ids=[str(i) for i in range(len(chunks))] 
            )
            st.session_state.file_processed = True
        st.success("文档已成功存入大脑！可以开始提问了。")
    else:
        collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

    user_input = st.chat_input("请输入你的问题...")
    
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # 先把当前问题加入历史记录
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("assistant"):
            with st.spinner("AI 正在检索和思考..."):
                # 【优化1：结合上下文进行检索】
                # 如果历史记录大于1条，就把上一句和这句拼起来去搜索，解决“这个活动”找不到的问题
                query_text = user_input
                if len(st.session_state.messages) > 1:
                    query_text = st.session_state.messages[-2]["content"] + " " + user_input
                
                results = collection.query(query_texts=[query_text], n_results=3)
                context = "\n\n".join(results['documents'][0])
                
                # 【优化2：把系统提示词和历史对话全部发给 AI】
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