"""
코드 작성 연습용 파일
"""

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_texts(extreacted_dir: Path) -> list[dict]:
    documents = []
    for txt_file in sorted(extreacted_dir.glob('*.txt')):
        text = txt_file.read_text(encoding='utf-8')
        documents.append({
            "source" : txt_file.stem,
            "text": text
        })
        
    return documents

def chunk_documents(documents: list[dict], chunk_size: int =500, chunk_overlap: int = 50) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=['\n\n', '\n'," ", ""])
    chunk = []
    for doc in documents:
        split_texts = splitter.split_text(doc['text'])
        for i, chunk_text in enumerate(split_texts):
            if chunk_text.strip():
                chunk.append({
                    'source' : doc['source'],
                    'chunk_index' : i,
                    "text": chunk_text.strip()
                })

    return chunk

