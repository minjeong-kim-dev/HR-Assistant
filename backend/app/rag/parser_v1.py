"""
File    : backend/app/rag/parser_v1.py
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
# from docling.document_converter import DocumentConverter, InputFormat
# from docling.datamodel.pipeline_options import (
#     PdfPipelineOptions,
#     EasyOcrOptions,
# )
# from docling.document_converter import PdfFormatOption


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


# def make_converter() -> DocumentConverter:
#     """Docling 텍스트 추출 컨버터 생성 (정상 인코딩 PDF 전용)."""
#     pipeline_options = PdfPipelineOptions()
#     pipeline_options.do_ocr = False
#     # 표 구조 감지 AI 모델(TableFormer)은 메모리를 많이 써서 bad_alloc 유발
#     pipeline_options.do_table_structure = False

#     return DocumentConverter(
#         format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
#     )


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


# def split_pdf(pdf_path: Path, output_dir: Path, chunk_size: int = 50):
#     """PDF를 chunk_size 페이지 단위로 분할."""
#     doc = fitz.open(pdf_path)
#     output_dir.mkdir(parents=True, exist_ok=True)

#     for start in range(0, len(doc), chunk_size):
#         end = min(start + chunk_size, len(doc))

#         new_pdf = fitz.open()
#         new_pdf.insert_pdf(doc, from_page=start, to_page=end - 1)

#         output_file = output_dir / f"{pdf_path.stem}_part_{start // chunk_size + 1}.pdf"
#         new_pdf.save(output_file)
#         new_pdf.close()

#         print(f"분할 완료: {output_file.name}")

#     doc.close()


# def convert_all_pdfs(pdf_dir: Path, md_dir: Path, split_dir: Path):
#     """data/raw의 모든 PDF를 data/markdown으로 변환."""
#     md_dir.mkdir(parents=True, exist_ok=True)

#     for pdf_file in sorted(pdf_dir.glob("*.pdf")):
#         try:
#             print(f"\n처리 시작: {pdf_file.name}")

#             doc = fitz.open(pdf_file)
#             page_count = len(doc)
#             doc.close()

#             print(f"페이지 수: {page_count}")

#             # 200페이지 초과면 분할
#             if page_count > 200:
#                 print("대용량 PDF -> 분할 진행")
#                 split_pdf(pdf_path=pdf_file, output_dir=split_dir, chunk_size=50)
#                 target_files = sorted(split_dir.glob(f"{pdf_file.stem}_part_*.pdf"))
#             else:
#                 target_files = [pdf_file]

#             # 한글 인코딩 깨짐 여부를 첫 번째 대상 파일로 판단
#             broken = has_broken_korean(target_files[0])
#             if broken:
#                 print("인코딩 불량 감지 -> 직접 OCR 모드로 변환")

#             # 변환
#             for target_pdf in target_files:
#                 output_file = md_dir / f"{target_pdf.stem}.md"

#                 if output_file.exists():
#                     print(f"건너뜀: {output_file.name}")
#                     continue

#                 print(f"변환 중: {target_pdf.name}")

#                 if broken:
#                     # 인코딩 깨짐 → PyMuPDF + EasyOCR 직접 사용
#                     # Docling OCR 파이프라인은 레이아웃 AI 모델까지 실행해서 OOM 발생
#                     convert_with_direct_ocr(target_pdf, output_file)
#                 else:
#                     # 정상 인코딩 → Docling 텍스트 추출
#                     converter = make_converter()
#                     result = converter.convert(str(target_pdf))
#                     markdown = result.document.export_to_markdown()
#                     with open(output_file, "w", encoding="utf-8") as f:
#                         f.write(markdown)
#                     print(f"변환 완료: {output_file.name}")

#         except Exception as e:
#             print(f"실패: {pdf_file.name}")
#             print(e)


# 직접 실행할 때만 동작 (import 시에는 실행 안 됨)
# if __name__ == "__main__":
#     convert_all_pdfs(
#         pdf_dir=Path("data/raw"),
#         md_dir=Path("data/markdown"),
#         split_dir=Path("data/raw/split"),
#     )