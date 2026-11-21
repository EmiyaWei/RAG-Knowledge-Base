from openai import OpenAI
import json
import os
from dotenv import load_dotenv
from tools import get_current_time, search_knowledge_base, get_weather, search_github_repos, extract_file_info, analyze_excel, TOOLS_SCHEMA
import chromadb
import time
# ... 其他 import ...

# 清除 ChromaDB 的全局系统缓存
chromadb.api.client.SharedSystemClient.clear_system_cache()
def log_execution(func):
    def wrapper(self, user_input, *args, **kwargs):
        print(f"📝 [系统日志] 用户发起请求：{user_input[:15]}...")
        result = func(self, user_input, *args, **kwargs)
        print(f"📝 [系统日志] AI 处理完毕。")
        return result
    return wrapper

class MyAgent:
    def __init__(self, name="小助手"):
        self.name = name
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
        self.chroma_client = chromadb.EphemeralClient()
        
        self.messages = [
            # 你想改猫娘设定就在这里改
            {"role": "system", "content": "你是一个傲娇的二次元猫娘，每次说话结尾都要带个'喵'。你可以查天气、查时间、查本地文档，还可以帮程序员搜索 GitHub 开源文档。请根据用户的意图使用相应的工具。"}
        ]

    # ==========================================
    # 原有的普通 run 方法（用于终端测试）
    # ==========================================
    @log_execution
    def run(self, user_input):
        print(f"[{self.name}] 正在思考...")
        self.messages.append({"role": "user", "content": user_input})

        for i in range(3):
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=self.messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto"
            )
            da_moxing_huida = response.choices[0].message
            
            if da_moxing_huida.tool_calls:
                self.messages.append(da_moxing_huida)
                for gongju in da_moxing_huida.tool_calls:
                    func_name = gongju.function.name
                    args = json.loads(gongju.function.arguments)
                    print(f"  🔧 正在调用工具：{func_name}")

                    if func_name == "get_current_time":
                        result = get_current_time()
                    elif func_name == "search_knowledge_base":
                        result = search_knowledge_base(self.chroma_client, args.get("query", ""))
                    elif func_name == "get_weather":
                        result = get_weather(args.get("city", "杭州"))
                    elif func_name == "search_github_repos":
                        result = search_github_repos(args.get("query", ""))
                    elif func_name == "extract_file_info":
                        result = extract_file_info(args.get("text", ""))
                    elif func_name == "analyze_excel":
                        result = analyze_excel(args.get("file_path", ""), args.get("question", ""))
                    else:
                        result = "未知工具"

                    self.messages.append({
                        "tool_call_id": gongju.id, 
                        "role": "tool", 
                        "name": func_name, 
                        "content": result
                    })
            else:
                break # 👈 昨天报错可能就是这行没缩进对

        final_response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=self.messages
        )
        final_answer = final_response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": final_answer})
        return final_answer

    # ==========================================
    # 新增的流式 stream_run 方法（用于网页打字机）
    # ==========================================
    @log_execution
    def stream_run(self, user_input):
        print(f"[{self.name}] 正在流式思考...")
        self.messages.append({"role": "user", "content": user_input})

        # 1. 先查工具
        for i in range(3):
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=self.messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto"
            )
            da_moxing_huida = response.choices[0].message
            
            if da_moxing_huida.tool_calls:
                self.messages.append(da_moxing_huida)
                for gongju in da_moxing_huida.tool_calls:
                    func_name = gongju.function.name
                    args = json.loads(gongju.function.arguments)
                    print(f"  🔧 正在调用工具：{func_name}")

                    if func_name == "get_current_time":
                        result = get_current_time()
                    elif func_name == "search_knowledge_base":
                        result = search_knowledge_base(self.chroma_client, args.get("query", ""))
                    elif func_name == "get_weather":
                        result = get_weather(args.get("city", "杭州"))
                    elif func_name == "search_github_repos":
                        result = search_github_repos(args.get("query", ""))
                    elif func_name == "analyze_excel":
                        result = analyze_excel(args.get("file_path", ""), args.get("question", ""))
                    else:
                        result = "未知工具"

                    self.messages.append({
                        "tool_call_id": gongju.id, 
                        "role": "tool", 
                        "name": func_name, 
                        "content": result
                    })
            else:
                break # 👈 这里的 break 也必须和 for 对齐，且缩进在 else 里面

        # 2. 流式输出打字机
        final_response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=self.messages,
            stream=True
        )
        
        full_answer = ""
        for chunk in final_response:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_answer += text
                yield text 
                
        self.messages.append({"role": "assistant", "content": full_answer})

if __name__ == "__main__":
    gou_dan = MyAgent(name="曹江韦的专属AI")
    # 测试 Excel 分析功能
    answer = gou_dan.run("帮本喵分析一下 员工工资表.xlsx 里 AI研发 部门的员工是谁，顺便看看平均工资是多少喵！")
    print(answer)