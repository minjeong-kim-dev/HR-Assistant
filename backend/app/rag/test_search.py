"""
File    : backend/app/rag/test_search.py
Author  : 김민정
Create  : 2026-06-08
Description :
    ChromaDB에 저장된 벡터를 검색 테스트하는 파일.
    질문을 KR-SBERT로 임베딩한 뒤 유사도 검색으로 관련 청크를 반환.

Modification History:
- 2026-06-08 (김민정): 최초 작성. ChromaDB 검색 테스트
"""
import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS")
client = chromadb.PersistentClient(path="data/vector_store")
collection = client.get_collection("hr_docs")

query = "연차휴가 며칠 받아요?"
query_embedding = model.encode(query).tolist() 

# ChromaDB에서 질문 벡터와 가장 비슷한 청크 3개를 찾기
results = collection.query(query_embeddings=[query_embedding], n_results=3)

for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"[출처: {meta['source']}]")
    print(doc[:100])
    print("---")
collection.query

