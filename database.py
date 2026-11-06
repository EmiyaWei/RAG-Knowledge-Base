import chromadb
from pypdf import PdfReader
import pdfplumber # 咱们昨天换的神器

# 👇 【升级点 1】使用 PersistentClient，将数据存入本地硬盘的 chroma_db 文件夹
def get_chroma_client():
    return chromadb.PersistentClient(path="./chroma_db")

def smart_split_text(text, chunk_size=500, overlap=50):
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + para + "\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def process_and_store_files(chroma_client, uploaded_files):
    collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
    
    for file in uploaded_files:
        # 👇 【升级点 2】避免重复上传同一个文件（先删掉旧的）
        try:
            collection.delete(where={"source": file.name})
        except Exception:
            pass 
            
        documents, metadatas, ids = [], [], []
        if file.name.endswith(".pdf"):
            with pdfplumber.open(file) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        chunks = smart_split_text(text, chunk_size=500, overlap=50)
                        for i, chunk in enumerate(chunks):
                            documents.append(chunk)
                            # 👇 核心：给每个切片打上“属于哪个文件”的标签
                            metadatas.append({"source": file.name, "page": page_num})
                            ids.append(f"{file.name}_p{page_num}_{i}")
        else:
            text = file.read().decode("utf-8")
            chunks = smart_split_text(text, chunk_size=500, overlap=50)
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({"source": file.name, "page": "TXT"})
                ids.append(f"{file.name}_txt_{i}")
        
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            
    return collection
