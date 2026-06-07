"""
File    : backend/app/rag/chunker.py
Author  : 김민정
Create  : 2026-06-07
Description :
    추출된 텍스트를 임베딩 가능한 크기의 청크로 분할.

Modification History:
- 2026-06-07 (김민정) : 최초 작성. RecursiveCharacterTextSplitter 로 청킹 구현
                        chunk_size=500, chunk_overlap=50 기본값 설정
                        11개 문서 → 1,460개 청크, 문서별 JSON 저장

"""

from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_texts(extracted_dir: Path) -> list[dict]:
    """
    data/extracted/ 의 모든 txt 파일을 읽어서 반환.
    각 파일을 하나의 문서로 취급하고, 출처(source) 정보를 함께 저장.
    """
    documents = []
    for txt_file in sorted(extracted_dir.glob("*.txt")):
        text = txt_file.read_text(encoding="utf-8")
        documents.append({
            "source": txt_file.stem,  # 파일명 = 출처 (ex: 연말정산_신고안내_2025)
            "text": text,
        })
        print(f"로드: {txt_file.name} ({len(text):,}자)")
    return documents


def chunk_documents(documents: list[dict], chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    """문서 리스트를 받아서 청크 리스트로 분할."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # 분할 우선순위 문단 -> 줄 -> 문장 -> 단어 -> 글자
        separators=["\n\n", "\n", ".", " ", ""],  
    )

    chunks = []
    for doc in documents:
        split_texts = splitter.split_text(doc["text"])
        for i, chunk_text in enumerate(split_texts):
            # 빈 청크(빈 문자열) 제외
            if chunk_text.strip():  
                chunks.append({
                    "source": doc["source"],
                    "chunk_index": i,
                    "text": chunk_text.strip(),
                })

    return chunks

# 함수 호출, 결과 저장/출력하는 코드
if __name__ == "__main__":
    """
    청킹된 데이터를 문서별로 분리해서 JSON 파일로 저장
    """
    import json

    extracted_dir = Path("data/extracted")

    print("=== 텍스트 로드 ===")
    documents = load_texts(extracted_dir)
    print(f"\n총 {len(documents)}개 문서 로드 완료\n")

    print("=== 청킹 시작 ===")
    chunks = chunk_documents(documents)
    print(f"\n총 청크 수: {len(chunks)}개")

    # 문서별로 청크를 분리해서 각각 JSON 파일로 저장
    chunks_dir = Path("data/chunks")
    chunks_dir.mkdir(parents=True, exist_ok=True)

    # source 기준으로 청크 묶기
    from collections import defaultdict
    chunks_by_source = defaultdict(list)
    for chunk in chunks:
        chunks_by_source[chunk["source"]].append(chunk)

    for source, source_chunks in chunks_by_source.items():
        out_path = chunks_dir / f"{source}.json"    # data/chunks/문서A.json
        out_path.write_text(
            json.dumps(source_chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"저장: {out_path.name} ({len(source_chunks)}개 청크)")

    print(f"\n총 {len(chunks_by_source)}개 파일, {len(chunks)}개 청크 저장 완료")
