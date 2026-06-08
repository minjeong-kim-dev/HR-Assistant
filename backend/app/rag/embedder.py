"""
File    : backend/app/rag/embedder.py
Author  : 김민정
Create  : 2026-06-08
Description :
    청크 텍스트를 KR-SBERT 모델로 임베딩하여 ChromaDB에 저장.
    저장 항목: id, 원본 텍스트, 768차원 벡터, 출처(source) 메타데이터.

Modification History:
- 2026-06-08 (김민정): 최초 작성. 청크 임베딩 후 ChromaDB 저장
"""
import json
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer

MODEL_NAME = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"

def load_chunks(chunks_dir: Path) -> list[dict]:
    """
    data/chunks/의 모든 JSON 파일을 읽어서 청크 리스트로 반환.
    """
    chunks = []
    for json_file in sorted(chunks_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding='utf-8'))
        chunks.extend(data)

    return chunks

def embed_and_store(chunks: list[dict], db_path: str = 'data/vector_store'):
    """
    청크를 임베딩해서 ChromaDB에 저장.
    """
    model = SentenceTransformer(MODEL_NAME)
    # 프로그램 꺼도 데이터 유지
    client = chromadb.PersistentClient(path=db_path)
    # 컬렉션이 있으면 가져오고 없으면 만들기
    collection = client.get_or_create_collection(name='hr_docs')

    texts = [chunk['text'] for chunk in chunks]
    ids = [f"{chunk['source']}_{chunk['chunk_index']}" for chunk in chunks]
    metadatas = [{"source": chunk["source"]} for chunk in chunks]

    print(f"임베딩 중... ({len(texts)}개 청크)")

    # 숫자 벡터로 변환 / show_progress_bar=True : 진행 상황을 터미널에 표시 옵션
    embeddings = model.encode(texts, show_progress_bar=True)

    collection.add(
        ids=ids,                        # 고유 ID
        documents=texts,                # 원본 텍스트
        embeddings=embeddings.tolist(), # 변환된 벡터
        metadatas=metadatas,            # 출처 정보
    )

    print(f"저장 완료: {collection.count()}개 저장됨")

if __name__ == "__main__":
    chunks = load_chunks(Path("data/chunks"))
    print(f"청크 로드: {len(chunks)}개")
    embed_and_store(chunks)
