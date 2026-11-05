import chromadb
import pdfplumber # 👈 换用这个神器

def get_chroma_client():
    return chromadb.EphemeralClient()

def smart_split_text(text, chunk_size=500, overlap=50):
    # （切片函数保持不变）
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
        documents, metadatas, ids = [], [], []
        if file.name.endswith(".pdf"):
            # 👇 这里换成了 pdfplumber 来提取文字
            with pdfplumber.open(file) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        chunks = smart_split_text(text, chunk_size=500, overlap=50)
                        for chunk in chunks:
                            documents.append(chunk)
                            metadatas.append({"source": file.name, "page": page_num})
                            ids.append(f"{file.name}_p{page_num}_{len(ids)}")
        else:
            text = file.read().decode("utf-8")
            chunks = smart_split_text(text, chunk_size=500, overlap=50)
            for chunk in chunks:
                documents.append(chunk)
                metadatas.append({"source": file.name, "page": "TXT"})
                ids.append(f"{file.name}_txt_{len(ids)}")
        
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            
    return collection
