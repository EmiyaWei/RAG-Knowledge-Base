import chromadb
from pypdf import PdfReader

def get_chroma_client():
    # 用内存模式防止云端报错
    return chromadb.EphemeralClient()

def process_and_store_files(chroma_client, uploaded_files):
    collection = chroma_client.get_or_create_collection(name="my_knowledge_base")
    for file in uploaded_files:
        documents, metadatas, ids = [], [], []
        if file.name.endswith(".pdf"):
            pdf_reader = PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                if text:
                    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
                    for chunk in chunks:
                        documents.append(chunk)
                        metadatas.append({"source": file.name, "page": page_num})
                        ids.append(f"{file.name}_p{page_num}_{len(ids)}")
        else:
            text = file.read().decode("utf-8")
            chunks = [text[i:i+500] for i in range(0, len(text), 500)]
            for chunk in chunks:
                documents.append(chunk)
                metadatas.append({"source": file.name, "page": "TXT"})
                ids.append(f"{file.name}_txt_{len(ids)}")
        
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return collection