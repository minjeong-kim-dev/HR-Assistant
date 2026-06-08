"""
File    : backend/app/rag/retriever.py
Author  : 김민정
Create  : 2026-06-08
Description :
    질문을 받아 ChromaDB에서 유사도 검색 후 관련 청크를 반환.
    embedder.py에서 저장한 KR-SBERT 벡터와 동일한 모델로 질문을 임베딩.

Modification History:
- 2026-06-08 (김민정): 최초 작성.
"""
from sentence_transformers import SentenceTransformer
import chromadb

MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
DB_PATH = "data/vector_store"
COLLECTION_NAME = "hr_docs"


# 모델과 컬렉션을 모듈 로드 시 한 번만 초기화
_model = None
_collection = None

def get_retriever():
    """
    _model 이 None 일 때: 로드, None이 아닐 때: 기존 것을 재사용
    """
    global _model, _collection
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
        client = chromadb.PersistentClient(path=DB_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _model, _collection


def search(query: str, n_results: int = 3) -> list[dict]:
    """
    질문과 유사한 청크를 ChromaDB에서 검색해서 반환.
    """
    model, collection = get_retriever()

    query_embedding = model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({
            "text": doc,
            "source": meta["source"],
        })
    
    return chunks


if __name__ == "__main__":
    questions = [
        "연차휴가는 며칠 받을 수 있나요?",
        "육아휴직 기간은 얼마나 되나요?",
        "연말정산 공제 항목이 뭐가 있나요?",
    ]

    for question in questions:
        print(f"\n질문: {question}")
        print("-" * 40)
        results = search(question)
        for i, chunk in enumerate(results, 1):
            print(f"[{i}] 출처: {chunk['source']}")
            print(chunk["text"][:150])
            print()