"""
File    : backend/app/rag/parser.py
Author  : 김민정
Create  : 2026-06-06
Description :

Modification History:
- 2026-06-03 (김민정) : 
"""

import fitz     # PyMuPDF 라이브러리 호출
from pathlib import Path


def has_broken_korean(pdf_path: Path, sample_pages: int = 5) -> bool:
    """
    PDF의 텍스트 인코딩이 깨져 있는지 확인.

    핵심 아이디어:
    한국어 문서에서 비ASCII 문자의 대부분은 한글 음절(가~힣)이어야 한다.
    비ASCII 문자는 많은데 한글 음절 비율이 5% 미만인 페이지가 있으면 인코딩이 깨진 것.

    이 방식의 장점:
    - ○, ※, △, → 같은 한국 문서 특수기호는 "비한글"이지만 개수가 적어 false positive 방지
    - 깨진 페이지는 아랍/키릴/그리스 등 엉뚱한 유니코드가 가득해서 확실히 걸림
    - 표지 한 장만 깨진 PDF도 즉시 감지 (페이지별 검사)
    """
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
    """
    PyMuPDF로 페이지를 이미지로 렌더링 후 EasyOCR로 직접 텍스트 추출.

    Docling의 OCR 파이프라인은 내부적으로 레이아웃 AI 모델(RT-DETR v2)까지
    실행해서 메모리 부족(OOM)이 발생하므로, 이 함수에서는 Docling을 쓰지 않음.
    페이지를 한 장씩 처리해서 메모리를 최소화.
    """
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
    """
    PyMuPDF로 PDF에서 텍스트 추출 (정상 인코딩 PDF 전용).

    get_text()는 PDF 내부의 텍스트 레이어를 직접 읽는다.
    ToUnicode 테이블이 정상이면 한글이 그대로 추출됨.
    페이지 구분자를 넣어두면 나중에 청킹할 때 페이지 경계를 활용할 수 있다.
    """
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
    """
    data/raw 의 모든 PDF를 텍스트로 추출해 data/extracted 에 저장.

    정상 PDF → extract_text() (빠름)
    깨진 PDF → convert_with_direct_ocr() (EasyOCR, 느림)
    """
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

