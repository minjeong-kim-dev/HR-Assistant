"""
File    : backend/app/rag/retriever.py
Author  : 김민정
Create  : 2026-06-08
Description :
    질문을 받아 ChromaDB에서 유사도 검색 후 관련 청크를 반환.
    Hybrid Search: BM25(키워드 일치) + 벡터(의미 유사도) 검색 결과를
    RRF(Reciprocal Rank Fusion)로 결합하여 검색 품질 향상.

Modification History:
- 2026-06-08 (김민정): 최초 작성.
- 2026-06-15 (김민정): MAX_SEARCH_RESULTS 상수 분리.
- 2026-06-16 (김민정): Hybrid Search 추가 (BM25 + 벡터 검색 RRF 결합).
"""
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import chromadb

MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
DB_PATH = "data/vector_store"
COLLECTION_NAME = "hr_docs"
MAX_SEARCH_RESULTS = 8
RRF_K = 60  # RRF 상수: 클수록 상위/하위 랭크 점수 차이가 줄어듦

# 모듈 로드 시 한 번만 초기화 (캐싱)
_model = None
_collection = None
_bm25 = None
_all_docs = None  # ChromaDB 전체 문서 캐시


def get_retriever():
    """벡터 검색용 KR-SBERT 모델과 ChromaDB 컬렉션을 초기화·캐싱."""
    global _model, _collection
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
        client = chromadb.PersistentClient(path=DB_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _model, _collection


def get_bm25():
    """
    BM25 인덱스를 한 번만 빌드하고 캐싱.
    ChromaDB 전체 문서를 로드해서 공백 기준 토크나이징 후 BM25 인덱스 생성.
    """
    global _bm25, _all_docs
    if _bm25 is None:
        _, collection = get_retriever()
        result = collection.get(include=["documents", "metadatas"])
        _all_docs = [
            {"id": doc_id, "text": doc, "source": meta["source"]}
            for doc_id, doc, meta in zip(
                result["ids"], result["documents"], result["metadatas"]
            )
        ]
        # 한국어는 공백 기준 분리 (형태소 분석기 없이도 BM25 효과 있음)
        tokenized = [doc["text"].split() for doc in _all_docs]
        _bm25 = BM25Okapi(tokenized)
    return _bm25, _all_docs


def search(query: str, n_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    """
    Hybrid Search로 질문과 관련된 청크를 반환.

    동작 방식:
        1. 벡터 검색: KR-SBERT로 질문을 임베딩 → ChromaDB 유사도 검색
        2. BM25 검색: 질문 키워드가 많이 포함된 청크 검색
        3. RRF 결합: 두 검색 결과의 순위를 점수로 변환해 합산 → 상위 n개 반환

    RRF 공식: score = 1/(rank_vector + K) + 1/(rank_bm25 + K)
    """
    model, collection = get_retriever()
    bm25, all_docs = get_bm25()

    candidate_count = n_results * 3  # 각 검색에서 후보를 넉넉히 가져옴

    # 1. 벡터 검색
    query_embedding = model.encode(query).tolist()
    vector_result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(candidate_count, len(all_docs)),
        include=[],  # ids는 항상 자동 반환되므로 명시 불필요
    )
    # {청크ID: 순위} — 1위부터 시작
    vector_ranks = {vid: rank + 1 for rank, vid in enumerate(vector_result["ids"][0])}

    # 2. BM25 검색
    bm25_scores = bm25.get_scores(query.split())
    top_bm25_indices = bm25_scores.argsort()[::-1][:candidate_count]
    bm25_ranks = {all_docs[i]["id"]: rank + 1 for rank, i in enumerate(top_bm25_indices)}

    # 3. RRF 점수 계산 (두 검색의 후보 합집합 대상)
    all_candidate_ids = set(vector_ranks) | set(bm25_ranks)
    rrf_scores = {
        doc_id: (
            1 / (vector_ranks.get(doc_id, candidate_count + 1) + RRF_K) +
            1 / (bm25_ranks.get(doc_id, candidate_count + 1) + RRF_K)
        )
        for doc_id in all_candidate_ids
    }

    # 4. RRF 점수 높은 순으로 상위 n_results 반환
    top_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:n_results]
    id_to_doc = {doc["id"]: doc for doc in all_docs}

    return [
        {"text": id_to_doc[vid]["text"], "source": id_to_doc[vid]["source"]}
        for vid in top_ids
        if vid in id_to_doc
    ]


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
