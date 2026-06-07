"""
File    : backend/app/rag/diagnose_pdf.py
Author  : 김민정
Create  : 2026-06-06
Description :
    parser.py 실행 전에 각 PDF의 한글 인코딩 상태를 미리 확인하는 진단 스크립트.
    "이 PDF가 OCR이 필요한가?" 를 눈으로 직접 확인할 수 있음.

    실행 방법: 프로젝트 루트에서
    python backend/app/rag/diagnose_pdf.py
"""

import sys
from pathlib import Path

import fitz

# 윈도우 터미널이 UTF-8을 출력할 수 있도록 강제 설정
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 프로젝트 루트를 sys.path에 추가해서 parser.py 함수만 임포트
# (parser.py의 __main__ 블록은 import 시 실행되지 않음)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend.app.rag.parser_v1 import has_broken_korean


def diagnose(pdf_path: Path):
    """PDF 한 개의 인코딩 상태와 샘플 텍스트를 출력."""
    doc = fitz.open(pdf_path)
    page_count = len(doc)

    raw_sample = doc[0].get_text()[:300].replace("\n", " ").strip()
    doc.close()

    broken = has_broken_korean(pdf_path)
    status = "[X] OCR 필요 (인코딩 깨짐)" if broken else "[O] 텍스트 추출 가능"

    # 출력 불가 문자(유니코드 사용자 영역 등)는 '?' 로 치환해서 보여줌
    safe_sample = raw_sample.encode("utf-8", errors="replace").decode("utf-8")

    print(f"\n{'='*60}")
    print(f"파일   : {pdf_path.name}")
    print(f"페이지 : {page_count}p")
    print(f"상태   : {status}")
    print(f"샘플   : {safe_sample[:150]}")


if __name__ == "__main__":
    pdf_dir = Path("data/raw")

    print("[ PDF 인코딩 진단 시작 ]")
    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        diagnose(pdf_file)

    print(f"\n{'='*60}")
    print("진단 완료. OCR 필요 파일은 변환 시 자동으로 EasyOCR 모드가 적용됩니다.")
