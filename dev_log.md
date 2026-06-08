# 개발 학습 일지

포트폴리오/이력서 작성 시 참고용. 왜 이렇게 구현했는지 기록.

---

## Day 02 · PDF 텍스트 추출 (parser.py)

### 왜 PyMuPDF를 선택했는가?
- 처음엔 Docling 라이브러리로 PDF → Markdown 변환 시도
- 문제 발생: 표 구조 감지 AI 모델(TableFormer, RT-DETR v2)이 OOM(메모리 부족) 유발
- 문서 대부분이 텍스트 중심 → 표/헤더 구조 보존 불필요
- 결론: PyMuPDF `get_text()` 직접 추출이 더 단순하고 안정적

### 한글 인코딩 깨짐 문제 (has_broken_korean)
- 일부 PDF는 폰트의 ToUnicode 테이블이 없어서 텍스트 추출 시 한글이 아랍/키릴 문자로 깨짐
- 감지 방법: 비ASCII 문자 중 한글 음절(가~힣, 0xAC00~0xD7A3) 비율이 5% 미만인 페이지가 있으면 깨진 것으로 판단
- ○, ※, → 같은 특수기호는 비한글이지만 개수가 적어 오탐 방지 가능
- 해결: PyMuPDF로 페이지를 이미지로 렌더링 후 EasyOCR로 직접 읽음

### OCR을 Docling이 아닌 EasyOCR 직접 사용한 이유
- Docling의 OCR 파이프라인은 텍스트 추출 외에 레이아웃 AI 모델까지 실행
- 메모리 부족 환경에서 RuntimeError 발생
- PyMuPDF로 페이지를 이미지로 렌더링 → EasyOCR 직접 호출로 우회
- 페이지를 한 장씩 처리해서 메모리 최소화 (150 DPI)

### 결과
- 11개 PDF → data/extracted/*.txt 추출 완료
- 정상 PDF: PyMuPDF (수초), 깨진 PDF 2개: EasyOCR (30분)

---

## Day 03 · 청크 분할 (chunker.py)

### 왜 청킹이 필요한가?
- 임베딩 모델은 입력 길이 제한이 있음 (보통 512토큰 내외)
- 문서 전체를 넣으면 의미가 뭉개짐 → 검색 정확도 하락
- 적당한 크기로 잘라야 질문과 관련된 부분만 정확히 찾아낼 수 있음

### RecursiveCharacterTextSplitter 선택 이유
- 문단(`\n\n`) → 줄(`\n`) → 문장(`.`) → 글자 순서로 자연스러운 경계에서 분할 시도
- 무조건 글자 수로만 자르는 것보다 문맥 보존이 좋음

### 청킹 전략
- chunk_size = 500: 청크 하나의 최대 글자 수
- chunk_overlap = 50: 청크 간 겹치는 글자 수
  - 겹침이 있어야 청크 경계에서 문맥이 잘리는 문제를 줄일 수 있음
  - 예: 청크1 끝 50자가 청크2 시작에도 포함됨

### 결과
- 11개 문서 → 1,460개 청크
- 문서별로 data/chunks/*.json 저장

---

## Day 04 · 임베딩 + ChromaDB 저장 (embedder.py)

### 임베딩이란?
- 텍스트를 숫자 벡터로 변환하는 것
- 모델에 저장된 문장이 아니라 "변환 규칙"이 저장되어 있음 → 처음 보는 문장도 즉시 변환 가능
- 의미가 비슷한 문장 → 비슷한 벡터 생성 → 거리 계산으로 검색 가능

### 모델 선택 이유
- `snunlp/KR-SBERT-V40K-klueNLI-augSTS`: 한국어 특화 임베딩 모델
- 벡터 크기: 768차원

### ChromaDB 구조
- 컬렉션 = 엑셀의 시트 1개
- 한 컬렉션에 다 넣는 이유: RAG에서 검색할 때 모든 문서를 동시에 비교해야 하기 때문
- 컬렉션을 나누는 경우: 완전히 다른 서비스 (HR문서 / 법무문서 / 재무문서) 를 따로 관리할 때
- 저장 항목: id(고유값) + documents(원본텍스트) + embeddings(벡터) + metadatas(출처)

### 트러블슈팅
- 검색 테스트 시 `collection.query(query_texts=["질문"])` 사용
- ChromaDB가 질문을 자기 내장 모델(384차원)로 임베딩함
- 저장된 벡터는 KR-SBERT(768차원) → 차원 불일치로 에러 발생
- 해결: 질문도 KR-SBERT로 직접 임베딩한 뒤 `query_embeddings=[벡터]` 로 넘김
  ```python
  # 에러 난 방식
  collection.query(query_texts=["연차휴가 며칠 받아요?"])

  # 수정한 방식
  query_embedding = model.encode("연차휴가 며칠 받아요?").tolist()
  collection.query(query_embeddings=[query_embedding])
  ```

### 결과
- 1,460개 청크 → 768차원 벡터로 변환
- data/vector_store/ 에 ChromaDB 저장 완료
- "연차휴가 며칠 받아요?" 검색 테스트 성공

---

## Day 05 · 유사도 검색 (retriever.py)

### Retriever란?
- 질문을 받아 ChromaDB에서 관련 청크를 찾아 반환하는 모듈
- RAG 파이프라인에서 "검색" 담당

### 흐름
```
질문 입력 → KR-SBERT 임베딩 → ChromaDB 유사도 검색 → 관련 청크 + 출처 반환
```

### 트러블슈팅
- 질문마다 모델을 새로 로드 → `Loading weights` 3번 출력, 느림
- 해결: `_model = None` 전역 변수로 캐싱, 첫 호출 시만 로드하고 이후 재사용

### 결과
- 3가지 질문 테스트 성공
- 연차휴가 / 육아휴직 / 연말정산 질문 모두 관련 문서에서 청크 반환 확인