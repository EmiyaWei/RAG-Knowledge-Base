import requests

# 【核心检查 1】确保这里是 /rag_chat，千万别写成 /chat 了！
url = "http://127.0.0.1:8000/rag_chat"

# 【核心检查 2】这里必须问一个只有你 PDF 文档里才有的问题！
# 比如你之前传的那个英语四级报名通知的 PDF
payload = {
    "question": "英语四级考试时间是什么时候？"
}

print("正在向后端发送请求...")
response = requests.post(url, json=payload)

if response.status_code == 200:
    print("✅ 接口调用成功！\n")
    
    # 把后端返回的完整 JSON 打印出来，让你看清楚它的全貌
    data = response.json()
    
    print("=== 使用的上下文 (Context) ===")
    # 这里会打印出系统从数据库里捞出来的原文片段
    print(data.get("context_used", "没有任何上下文！")) 
    
    print("\n=== AI 的回答 ===")
    print(data["answer"])
else:
    print("❌ 报错了，状态码：", response.status_code)
    print(response.text)