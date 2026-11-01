from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
import chromadb

load_dotenv()
MY_API_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=MY_API_KEY, base_url="https://api.deepseek.com")

# 初始化向量数据库
# 把数据库保存在当前目录下的 chroma_db 文件夹里
chroma_client = chromadb.PersistentClient(path="./chroma_db")
# 假设你之前已经在本地存入过数据（如果没有，先跑一次本地的 app.py 传个文件）
collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

app = FastAPI(title="我的企业级 RAG 接口")

# 定义前端传过来的数据格式
class ChatRequest(BaseModel):
    question: str

@app.post("/rag_chat")
async def rag_chat(request: ChatRequest):
    user_q = request.question
    
    # 1. 去向量数据库里检索相关的段落
    results = collection.query(query_texts=[user_q], n_results=2)
    
    # 2. 把检索到的段落拼成上下文
    context = "\n\n".join(results['documents'][0]) if results['documents'] else "未找到相关文档。"
    
    # 3. 组装 Prompt 发给大模型
    system_prompt = f"请根据以下上下文回答用户问题，如果上下文中没有，请说不知道。\n\n上下文：\n{context}"
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_q}
        ]
    )
    
    return {
        "question": user_q,
        "context_used": context, # 把用到的上下文也返回给前端，方便前端做溯源展示
        "answer": response.choices[0].message.content
    }