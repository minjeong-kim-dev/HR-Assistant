# HR Assistant
### 기업 인사·행정 규정 문서 기반 AI 질의응답 시스템

---

## 1. 프로젝트 기간

2026.06.01 ~ 2026.06.30

---

## 2. 프로젝트 개요

### 2.1. 프로젝트 배경 및 목적

이전 직장에서 경영 지원 업무를 담당하며 직원들의 출장 경비 처리를 맡았습니다.
처리 기준이 케이스마다 달라서, 매번 사내 규정 문서를 직접 뒤져서 확인해야 했습니다.

> "이 경비는 처리가 되는 건가? 한도가 얼마지? 증빙은 뭐가 필요하지?"

문서는 있었지만, 수십 페이지 중 원하는 내용을 찾는 데만 시간이 걸렸습니다.
**"그냥 물어보면 바로 답해주면 얼마나 좋을까"** — 이 경험이 이 프로젝트의 출발점입니다.

현재는 재직 중이 아니어서 실제 사내 문서를 구하기 어렵습니다.
대신 공개된 노동 관련 규정 문서(연차휴가, 육아휴직, 연말정산, 근로시간)를 활용해 동일한 구조로 구현했습니다.

---

### 2.2. 프로젝트 목표

사내 규정 PDF를 학습시켜, 직원이 자연어로 질문하면 관련 내용을 검색해 **출처와 함께** 답변하는 AI 어시스턴트 구축

---

### 2.3. 기대 효과

| 관점 | 효과 |
|---|---|
| 직원 | 수십 페이지 문서를 직접 뒤지지 않아도 됨 → **규정 확인 시간 단축** |
| HR 담당자 | "연차가 며칠이에요?" 같은 반복 문의 응대 횟수 감소 → **핵심 업무 집중 가능** |
| 기업 | 동일한 인력으로 더 많은 업무 처리 가능 → **업무 효율 향상** |

---

## 3. 시스템 구현

### 3.1. 문서 데이터

| 항목 | 내용 |
|---|---|
| 문서 종류 | 연차휴가, 육아휴직, 연말정산, 근로시간·휴게시간·휴일 |
| 형식 | PDF (총 11개 파일) |
| 청크 수 | 1,460개 |
| 청크 크기 | 500자, 오버랩 50자 |
| 임베딩 모델 | KR-SBERT (snunlp/KR-SBERT-V40K-klueNLI-augSTS, 768차원) |

---

### 3.2. RAG 파이프라인

```
[PDF 문서]
    │
    ▼
[PyMuPDF 텍스트 추출]  ←── 한글 깨짐 감지 시 EasyOCR fallback
    │
    ▼
[RecursiveCharacterTextSplitter]  chunk_size=500, overlap=50
    │  500자 단위로 자르되 문장이 잘리지 않도록 재귀적으로 분할
    ▼
[KR-SBERT 임베딩]  텍스트 → 768차원 숫자 벡터로 변환
    │
    ▼
[ChromaDB]  벡터 저장 + 유사도 검색
```

---

### 3.3. LangGraph 라우팅 구조

```
[사용자 질문]
    │
    ▼
[router 노드]  HR 관련 여부 판단
    │
    ├── rag  →  [ChromaDB 검색] → [문서 기반 답변 + 출처]
    │
    └── llm  →  [LLM 직접 답변]
```

---

## 4. 주요 기능 및 결과

### 4.1. 주요 기능

- **문서 기반 Q&A**: 사내 규정 PDF에서 관련 내용 검색 후 출처 포함 답변
- **일반 Q&A**: 문서와 무관한 질문은 LLM이 직접 답변
- **자동 경로 분기**: 질문 유형에 따라 두 경로 자동 선택
- **연속 대화**: 이전 맥락을 기억하며 대화 가능
- **대화 기록 저장**: 모든 질문/답변/경로를 SQLite DB에 저장

---

### 4.2. 시스템 아키텍처

```
[Streamlit UI]
    │  질문 + 대화 히스토리 전달
    ▼
[FastAPI /chat 엔드포인트]
    │
    ├── [LangGraph]
    │       ├── router → 경로 결정 (rag / llm)
    │       ├── rag_node → ChromaDB 검색 + 답변 생성
    │       └── llm_node → LLM 직접 답변
    │
    └── [SQLite] 대화 내역 저장
```

---

### 4.3. 디렉토리 구조

```
project01/
├── backend/
│   └── app/
│       ├── rag/
│       │   ├── parser.py       # PDF 텍스트 추출 (PyMuPDF + EasyOCR)
│       │   ├── chunker.py      # 청크 분할
│       │   ├── embedder.py     # 임베딩 + ChromaDB 저장
│       │   └── retriever.py    # 유사도 검색
│       ├── graph/
│       │   └── graph.py        # LangGraph 라우팅 그래프
│       ├── api/routes/
│       │   └── chat.py         # /chat 엔드포인트
│       ├── database.py         # SQLite 모델 + 연결
│       ├── logger.py           # 로깅 설정
│       └── main.py             # FastAPI 앱
├── frontend/
│   └── app.py                  # Streamlit UI
├── data/
│   ├── raw/                    # 원본 PDF (git 제외)
│   ├── extracted/              # 추출된 텍스트
│   ├── chunks/                 # 청크 JSON
│   └── vector_store/           # ChromaDB (git 제외)
├── logs/                       # 실행 로그 (git 제외)
└── dev_log.md                  # 개발 학습 일지
```

---

### 4.4. RAG 품질 평가 (RAGAS)

RAG 파이프라인이 실제로 잘 작동하는지 RAGAS 프레임워크로 정량 평가했습니다.

> **RAGAS**: 질문 → RAG 실행 → 답변/출처를 자동으로 수집하고, 4가지 지표로 품질을 0~1 사이 점수로 측정하는 평가 프레임워크

**평가 데이터셋**: 연차휴가·육아휴직·연말정산·근로시간 관련 Q&A 16개 (`data/ragas_dataset.json`)

| 지표 | 점수 | 의미 |
|---|---|---|
| Context Precision | **0.97** | 검색된 청크가 질문에 관련 있는가 → 검색 품질 우수 |
| Context Recall | **0.47** | 정답에 필요한 내용이 청크에 포함됐는가 → 청크 수 한계 |
| Faithfulness | **0.34** | 답변이 문서 내용에만 근거하는가 → 프롬프트 강화 후 개선 |
| Answer Relevancy | 측정 불가 | RAGAS의 한국어 처리 한계로 수치 왜곡 |

**개선 과정**: 프롬프트를 "문서에 없는 내용은 답하지 마세요" → "반드시 문서에 명시된 내용만 답하고 절대 추가하지 마세요"로 강화 후 Faithfulness 0.24 → 0.34 향상

---

### 4.5. 실행 모니터링 (LangSmith)

LangSmith를 연동해 LangGraph 실행 흐름을 실시간으로 추적합니다.

> **LangSmith**: LangChain/LangGraph 실행 흐름을 웹 대시보드에서 시각화하는 모니터링 도구. `.env`에 환경변수 2줄 추가만으로 자동 연동.

**확인 가능한 정보**
- 질문이 `router → rag_node` 또는 `router → llm_node` 중 어디로 갔는지
- 각 노드의 입력/출력 내용 및 대화 히스토리 전달 여부
- 노드별 처리 시간 및 질문당 API 비용

---

## 5. 설치 및 실행

### 환경 설정

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 환경 변수 설정

`.env` 파일 생성:

```
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
```

### RAG 파이프라인 실행 (최초 1회)

```bash
python -m backend.app.rag.parser     # PDF 텍스트 추출
python -m backend.app.rag.chunker    # 청크 분할
python -m backend.app.rag.embedder   # 임베딩 + ChromaDB 저장
```

### 서버 실행

```bash
# FastAPI 서버 (터미널 1)
uvicorn backend.app.main:app --reload

# Streamlit UI (터미널 2)
streamlit run frontend/app.py
```

---

## 6. 트러블슈팅

### 1. Docling OOM → PyMuPDF로 전환
- **문제**: PDF 변환 라이브러리 Docling 사용 시 OOM(메모리 부족) 에러
- **원인**: Docling 내부 AI 모델(TableFormer, RT-DETR v2)이 RAM 과다 사용
- **해결**: PyMuPDF `get_text()`로 텍스트 직접 추출로 전환
- **결과**: 메모리 문제 해결, 처리 속도 수 분 → 수 초

### 2. 한글 PDF 인코딩 깨짐 → EasyOCR fallback
- **문제**: 일부 PDF 텍스트 추출 시 한글이 아랍/키릴 문자로 깨짐
- **원인**: PDF 폰트에 ToUnicode 테이블이 없어 PyMuPDF가 문자 디코딩 실패
- **해결**: 한글 음절(가~힣) 비율로 깨짐 자동 감지 → EasyOCR로 재추출
- **결과**: 11개 중 2개 OCR 처리, 전체 텍스트 정상 추출

### 3. ChromaDB 벡터 차원 불일치
- **문제**: `Collection expecting dimension 768, got 384` 에러
- **원인**: `query_texts` 사용 시 ChromaDB 내장 모델(384차원)이 임베딩 → 저장 시 모델(768차원)과 불일치
- **해결**: `query_embeddings` 사용 — 질문도 KR-SBERT로 직접 임베딩해서 전달
- **결과**: 동일 모델로 저장/검색하여 차원 일치, 검색 정상 동작

### 4. LangChain 메시지 리스트 중첩 에러
- **문제**: `NotImplementedError: Message as a sequence must be (role string, template)`
- **원인**: `messages` 리스트 안에 `history_messages` 리스트를 통째로 삽입 → 리스트 안에 리스트 중첩
- **해결**: `*history_messages`로 언패킹하여 개별 항목으로 삽입
- **결과**: 대화 히스토리 정상 전달, 맥락 유지

### 5. RAG의 개요 질문 한계
- **문제**: "전체적으로 알려줘" 같은 개요 요청 시 RAG 답변보다 LLM 직접 답변이 더 풍부함
- **원인**: RAG는 유사도 검색으로 찾은 청크 3개만 참고 → 전체 개요 설명에 컨텍스트 부족
- **현재**: 특정 사실 질문 → RAG 유리 / 개요 설명 → LLM 유리 (알려진 한계)
- **개선 방향**: 질문 유형(사실 vs 개요)을 추가로 분류하거나 검색 청크 수 증가 고려

---

## 7. 결론 및 향후 개선 방향

본 프로젝트는 사내 규정 문서를 PDF 형태로 보유하고 있지만 활용이 어려운 기업 환경에서, 직원이 자연어로 질문하면 관련 규정을 즉시 찾아 출처와 함께 답변하는 AI 어시스턴트를 구현했습니다.

**향후 개선 방향**
- 실제 기업 사내 문서(출장 경비, 복지 규정 등)로 확장
- 청크 수 증가 또는 질문 유형 분류 추가로 개요 질문 답변 품질 개선
- 답변 정확도 평가 지표(RAGAS 등) 도입

---

## 8. 기술 스택

| 분류 | 기술 |
|---|---|
| Language | Python 3.11 |
| Agent Framework | LangChain, LangGraph |
| LLM | gpt-4o-mini |
| Embedding | KR-SBERT (snunlp/KR-SBERT-V40K-klueNLI-augSTS) |
| Vector DB | ChromaDB |
| PDF 파싱 | PyMuPDF, EasyOCR |
| API Server | FastAPI |
| DB | SQLite + SQLAlchemy |
| UI | Streamlit |
