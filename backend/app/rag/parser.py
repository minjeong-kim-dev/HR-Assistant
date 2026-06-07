"""
File    : backend/app/rag/parser.py
Author  : 김민정
Create  : 2026-06-06
Description :

Modification History:
- 2026-06-03 (김민정) : 최초 작성. Docling 기반 PDF→Markdown 변환 구현
- 2026-06-06 (김민정) : PyMuPDF 직접 텍스트 추출 방식으로 전환
                        Docling 제거, has_broken_korean() 으로 인코딩 감지
                        인코딩 깨진 PDF는 EasyOCR fallback 처리
                        11개 PDF → data/extracted/*.txt 추출 완료
"""

import fitz     # PyMuPDF 라이브러리 호출
from pathlib import Path


def has_broken_korean(pdf_path: Path, sample_pages: int = 5) -> bool:
    """PDF의 텍스트 인코딩이 깨져 있는지 확인. 한글 음절 비율로 판단."""
    doc = fitz.open(pdf_path)
    total_pages = min(sample_pages, len(doc))

    total_non_ascii = 0
    total_hangul = 0

    for i in range(total_pages):
        text = doc[i].get_text()

        page_non_ascii = 0
        page_hangul = 0

        for ch in text:
            if ch.isspace() or ch.isdigit() or ch.isascii():
                continue
            page_non_ascii += 1
            cp = ord(ch)
            if 0xAC00 <= cp <= 0xD7A3:  # 한글 완성형 음절만 카운트
                page_hangul += 1

        # 페이지에 비ASCII 문자가 충분한데 한글이 거의 없으면 즉시 깨진 것으로 판단
        if page_non_ascii > 8 and page_hangul / page_non_ascii < 0.05:
            doc.close()
            return True

        total_non_ascii += page_non_ascii
        total_hangul += page_hangul

    doc.close()

    if total_non_ascii == 0:
        return True  # 텍스트가 없으면 스캔 PDF → OCR 필요

    # 전체 샘플에서도 한글 비율이 너무 낮으면 깨진 것으로 판단
    return total_hangul / total_non_ascii < 0.1


def convert_with_direct_ocr(pdf_path: Path, output_file: Path):
    """인코딩이 깨진 PDF를 페이지 이미지로 렌더링 후 EasyOCR로 텍스트 추출."""
    import numpy as np
    import easyocr

    reader = easyocr.Reader(["ko", "en"], gpu=False)
    doc = fitz.open(pdf_path)
    pages_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 150 DPI로 렌더링 — 메모리 절약 (72 DPI가 기본, 배율 150/72 ≈ 2.08)
        pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )

        results = reader.readtext(img, detail=1)
        page_text = "\n".join(
            text for _, text, conf in results if conf > 0.3 and text.strip()
        )
        pages_text.append(f"## {page_num + 1}페이지\n\n{page_text}")
        print(f"  {page_num + 1}/{len(doc)}p 완료")

    doc.close()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(pages_text))

    print(f"변환 완료: {output_file.name}")


def extract_text(pdf_path: Path) -> str:
    """PyMuPDF로 PDF 텍스트 직접 추출. 페이지 사이는 빈 줄 두 개로 구분."""
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        text = doc[page_num].get_text().strip()
        if text:  # 빈 페이지 제외
            pages.append(text)

    doc.close()
    # 페이지 사이를 빈 줄 두 개로 구분 → 청킹 시 문단 경계로 활용
    return "\n\n".join(pages)


def extract_all_pdfs(pdf_dir: Path, output_dir: Path):
    """data/raw 의 모든 PDF를 data/extracted 에 txt로 저장. 깨진 PDF는 OCR 처리."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        output_file = output_dir / f"{pdf_file.stem}.txt"

        if output_file.exists():
            print(f"건너뜀: {output_file.name}")
            continue

        print(f"\n처리 중: {pdf_file.name}")

        if has_broken_korean(pdf_file):
            print("  인코딩 깨짐 감지 → OCR 모드")
            convert_with_direct_ocr(pdf_file, output_file)
        else:
            text = extract_text(pdf_file)
            output_file.write_text(text, encoding="utf-8")
            print(f"  완료: {output_file.name} ({len(text):,}자)")


if __name__ == "__main__":
    extract_all_pdfs(
        pdf_dir=Path("data/raw"),
        output_dir=Path("data/extracted"),
    )

