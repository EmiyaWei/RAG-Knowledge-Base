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
        
        # 1. 向量检索：捞语义最相近的 3 段
        vector_results = collection.query(query_texts=[query], n_results=3)
        
        # 2. 关键词检索：暴力捞包含 query 原词的段落（最多捞3段）
        keyword_results = collection.query(
            query_texts=[query],
            n_results=3,
            # 这里的 $contains 相当于 SQL 里的 LIKE '%query%'
            where_document={"$contains": query} 
        )
        
        # 3. 把两拨捞出来的结果合并去重
        final_docs = []
        final_metas = []
        
        # 先装向量检索捞出来的
        if vector_results['documents'] and len(vector_results['documents'][0]) > 0:
            for i in range(len(vector_results['documents'][0])):
                final_docs.append(vector_results['documents'][0][i])
                final_metas.append(vector_results['metadatas'][0][i])
                
        # 再装关键词暴力捞出来的（如果有的话）
        if keyword_results['documents'] and len(keyword_results['documents'][0]) > 0:
            for i in range(len(keyword_results['documents'][0])):
                # 去重：如果这段内容已经在里面了，就不重复加了
                if keyword_results['documents'][0][i] not in final_docs:
                    final_docs.append(keyword_results['documents'][0][i])
                    final_metas.append(keyword_results['metadatas'][0][i])
        
        # 4. 拼装成最终上下文
        context = ""
        for i in range(len(final_docs)):
            doc = final_docs[i]
            meta = final_metas[i]
            context += f"[来源: {meta['source']} 第{meta['page']}页]: {doc}\n\n"
            
        return context if context else "未找到相关内容。"
    except Exception as e:
        return f"检索失败: {str(e)}"

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
    },
    {
    "type": "function", 
    "function": {
        "name": "search_github_repos", 
        "description": "当用户想要找代码、找开源项目、或者查 GitHub 上的相关技术时，使用此工具搜索。", 
        "parameters": {
            "type": "object", 
            "properties": {
                "query": {"type": "string", "description": "搜索关键词，例如：RAG、大模型"}
            }, 
            "required": ["query"]
            }
        }
    }
]

def search_github_repos(query: str):
    """
    搜索 GitHub 上的开源项目
    """
    try:
        # 这是 GitHub 官方提供的免费接口，不需要填 Key
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=3"
        # 必须加请求头，否则 GitHub 会拒绝
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if not items:
                return "没有搜到相关的开源项目。"
            
            # 咱们今天刚学了 f-string 和 enumerate，用起来！
            result_text = f"为你找到关于 '{query}' 最火的 3 个开源项目：\n"
            for index, repo in enumerate(items, start=1):
                name = repo["full_name"]
                stars = repo["stargazers_count"]
                desc = repo["description"]
                url_link = repo["html_url"]
                result_text += f"{index}. 名称：{name} (🌟 {stars} stars)\n   简介：{desc}\n   链接：{url_link}\n\n"
            return result_text
        else:
            return "Github 搜索接口报错。"
    except Exception as e:
        return f"搜索失败：{str(e)}"