from datetime import datetime
from duckduckgo_search import DDGS

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def search_knowledge_base(chroma_client, query: str):
    try:
        collection = chroma_client.get_collection(name="my_knowledge_base")
        if collection.count() == 0:
            return "知识库为空，请先上传文档。"
        results = collection.query(query_texts=[query], n_results=3)
        context = ""
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                context += f"[来源: {meta['source']} 第{meta['page']}页]: {doc}\n\n"
        return context if context else "未找到相关内容。"
    except Exception:
        return "检索失败，请使用通用知识回答。"

def search_internet(query: str):
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return "没有搜到相关信息。"
        context = "以下是互联网实时搜索结果：\n"
        for res in results:
            context += f"- 标题: {res['title']}\n  摘要: {res['body']}\n\n"
        return context
    except Exception as e:
        return "联网搜索失败（网络连接超时）。请直接使用你内置的通用知识来回答用户的问题，不要重试。"