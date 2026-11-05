from datetime import datetime
from duckduckgo_search import DDGS
import requests

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def search_knowledge_base(chroma_client, query: str):
    try:
        collection = chroma_client.get_collection(name="my_knowledge_base")
        if collection.count() == 0:
            return "知识库为空，请先上传文档。"
        results = collection.query(query_texts=[query], n_results=5)
        context = ""
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                context += f"[来源: {meta['source']} 第{meta['page']}页]: {doc}\n\n"
        
        # 👇 【新增】如果抓出来的字少于 20 个，说明肯定没查准，直接报错
        if len(context.strip()) < 20:
            return "【系统提示】未检索到相关有效内容，请直接告诉用户文档中没有提及。"
            
        return context if context else "未找到相关内容。"
    except Exception:
        return "检索失败。"

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
        return "联网搜索失败。"

def get_weather(city: str):
    try:
        url = f"https://wttr.in/{city}?format=3&lang=zh"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return f"实时天气信息：{response.text.strip()}"
        else:
            return "天气查询失败。"
    except Exception as e:
        return f"天气查询出错：{str(e)}"

TOOLS_SCHEMA = [
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
            "description": "当用户询问他们上传的文件、资料、具体条款、考试时间、或者任何本地私有文档的内容时，必须、绝对要优先使用此工具！严禁使用联网搜索去查本地文档！", 
            "parameters": {
                "type": "object", 
                "properties": {"query": {"type": "string"}}, 
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "search_internet", 
            "description": "联网搜索实时新闻等信息。", 
            "parameters": {
                "type": "object", 
                "properties": {"query": {"type": "string"}}, 
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "get_weather", 
            "description": "查询某个城市的实时天气。", 
            "parameters": {
                "type": "object", 
                "properties": {"city": {"type": "string"}}, 
                "required": ["city"]
            }
        }
    }
]
