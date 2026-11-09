import sqlite3

# 1. 初始化数据库并建表（就像在 Excel 里新建一个 Sheet）
def init_db():
    # 连接（或者创建）一个名叫 chat_history.db 的文件
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    
    # 建表：如果这个表不存在，就创建一个包含 id, role, content 的表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# 2. 保存一条聊天记录（插入一行数据）
def save_message(role, content):
    try:
        conn = sqlite3.connect("chat_history.db")
        cursor = conn.cursor()
        # 这里的 ? 是占位符，防止 SQL 注入（超重要的大厂知识点）
        cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
        conn.commit()
    except Exception as e:
        print(f"保存失败：{e}")
    finally:
        conn.close() # 不管成不成功，最后一定要关掉数据库连接

# 3. 获取所有聊天记录（查询数据）
def get_all_messages():
    try:
        conn = sqlite3.connect("chat_history.db")
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM messages")
        rows = cursor.fetchall() # 获取所有结果
        
        # 把数据库里的元组（比如 ('user', '你好')），转换成咱们大模型需要的字典格式
        messages = []
        for row in rows:
            messages.append({"role": row[0], "content": row[1]})
        return messages
    except Exception as e:
        return []
    finally:
        conn.close()

# 4. 清空所有历史记录
def clear_messages():
    try:
        conn = sqlite3.connect("chat_history.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

# 第一次导入这个文件时，自动初始化数据库
init_db()