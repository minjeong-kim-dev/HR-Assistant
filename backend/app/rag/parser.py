"""
File    : backend/app/rag/parser.py
Author  : 김민정
Create  : 2026-06-03
Description :

Modification History:
- 2026-06-03 (김민정) : 최초 작성
                        PDF를 Markdown으로 변환하는 기본 로직 구현
                        200페이지 초과 PDF는 50페이지 단위로 분할 후 변환 (OOM 방지)
                        DocumentConverter()를 단일 객체로 생성하여 전체 PDF에 공통 적용
                        
- 2026-06-03 (Claude) : 한글 인코딩 깨짐 문제 대응
                        has_broken_korean() 추가 - 변환 전 ToUnicode 테이블 불량 여부 자동 감지
                        make_converter() 추가 - 인코딩 불량 PDF는 EasyOCR(ko/en) 모드로 전환
                        converter를 PDF별로 분기 생성하도록 변경
"""

from pathlib import Path

import fitz     # PyMuPDF 라이브러리 호출
from docling.document_converter import DocumentConverter, InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
)
from docling.document_converter import PdfFormatOption


def has_broken_korean(pdf_path: Path, sample_pages: int = 3) -> bool:
    """
    PDF의 텍스트 인코딩이 깨져 있는지 확인.
    - ToUnicode 테이블이 없으면 /\_XXXX 형태의 glyph ID가 추출됨
    - 잘못된 매핑이면 한글 대신 아랍·인도계 문자 등 엉뚱한 유니코드가 추출됨
    """
    doc = fitz.open(pdf_path)
    total = min(sample_pages, len(doc))

    glyph_id_chars = 0
    non_korean_cjk = 0
    total_chars = 0

    for i in range(total):
        text = doc[i].get_text()
        for ch in text:
            if ch.isspace():
                continue
            total_chars += 1
            cp = ord(ch)
            # /\_XXXX 형태 → 아스키 숫자·슬래시·언더스코어로만 구성
            if ch in "/_\\" or ch.isdigit():
                glyph_id_chars += 1
            # 한글 범위 밖의 비ASCII 문자 (아랍, 인도계, etc.)
            elif cp > 127 and not (0xAC00 <= cp <= 0xD7A3) and not (0x3000 <= cp <= 0x9FFF):
                non_korean_cjk += 1

    doc.close()

    if total_chars == 0:
        return True  # 텍스트가 전혀 없으면 스캔 PDF → OCR 필요
    broken_ratio = (glyph_id_chars + non_korean_cjk) / total_chars
    return broken_ratio > 0.3


def make_converter(use_ocr: bool) -> DocumentConverter:
    """OCR 사용 여부에 따라 Docling 컨버터 생성."""
    pipeline_options = PdfPipelineOptions()

    if use_ocr:
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = EasyOcrOptions(lang=["ko", "en"])
    else:
        pipeline_options.do_ocr = False

    # OOM 방지: 표 구조 감지 모델은 무거우므로 필요 없으면 비활성화 가능
    # pipeline_options.do_table_structure = False

    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )


def split_pdf(pdf_path: Path, output_dir: Path, chunk_size: int = 50):
    """PDF를 chunk_size 페이지 단위로 분할."""
    doc = fitz.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    for start in range(0, len(doc), chunk_size):
        end = min(start + chunk_size, len(doc))

        new_pdf = fitz.open()
        new_pdf.insert_pdf(doc, from_page=start, to_page=end - 1)

        output_file = output_dir / f"{pdf_path.stem}_part_{start // chunk_size + 1}.pdf"
        new_pdf.save(output_file)
        new_pdf.close()

        print(f"분할 완료: {output_file.name}")

    doc.close()


pdf_dir = Path("data/raw")
md_dir = Path("data/markdown")
split_dir = Path("data/raw/split")

md_dir.mkdir(parents=True, exist_ok=True)

# ======================================
# PDF 처리 - 200페이지 초과시 페이지 분리
# ======================================

for pdf_file in pdf_dir.glob("*.pdf"):
    try:
        print(f"\n처리 시작: {pdf_file.name}")

        doc = fitz.open(pdf_file)
        page_count = len(doc)
        doc.close()

        print(f"페이지 수: {page_count}")

        # 200페이지 초과면 분할
        if page_count > 200:
            print("대용량 PDF → 분할 진행")
            split_pdf(pdf_path=pdf_file, output_dir=split_dir, chunk_size=50)
            target_files = sorted(split_dir.glob(f"{pdf_file.stem}_part_*.pdf"))
        else:
            target_files = [pdf_file]

        # 한글 인코딩 깨짐 여부를 첫 번째 대상 파일로 판단
        broken = has_broken_korean(target_files[0])
        converter = make_converter(use_ocr=broken)
        if broken:
            print("인코딩 불량 감지 → OCR 모드로 변환")

        # 변환
        for target_pdf in target_files:
            output_file = md_dir / f"{target_pdf.stem}.md"

            if output_file.exists():
                print(f"건너뜀: {output_file.name}")
                continue

            print(f"변환 중: {target_pdf.name}")
            result = converter.convert(str(target_pdf))
            markdown = result.document.export_to_markdown()

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown)

            print(f"변환 완료: {output_file.name}")

    except Exception as e:
        print(f"실패: {pdf_file.name}")
        print(e)