# 개발 학습 일지

포트폴리오/이력서 작성 시 참고용. 왜 이렇게 구현했는지 기록.

---

## Day 02 · PDF 텍스트 추출 (parser.py)

### 왜 PyMuPDF를 선택했는가?
- 처음엔 Docling 라이브러리로 PDF → Markdown 변환 시도
- 문제 발생: Docling이 표 구조 감지를 위해 AI 모델(TableFormer, RT-DETR v2)을 내부적으로 실행하는데, 이 모델이 메모리를 너무 많이 써서 OOM(Out of Memory, 메모리 부족) 에러 발생
- 우리 문서는 대부분 텍스트 중심 → 표/헤더 구조를 굳이 Markdown으로 변환할 필요 없음
- 결론: PyMuPDF의 `get_text()` 로 텍스트만 직접 추출하는 방식이 더 단순하고 안정적

### 한글 인코딩 깨짐 문제 (has_broken_korean)
- 일부 PDF는 폰트 내부에 ToUnicode 테이블이 없어서, PyMuPDF가 텍스트를 추출할 때 한글이 아랍/키릴 문자로 깨짐
- 감지 방법: 페이지에서 비ASCII 문자(영어/숫자/공백 제외) 중 한글 음절(가~힣, 유니코드 0xAC00~0xD7A3) 비율이 5% 미만이면 "깨진 PDF"로 판단
  - ○, ※, → 같은 특수기호는 비한글이지만 개수가 적어 오탐(잘못된 탐지) 방지 가능
- 해결: 깨진 PDF는 PyMuPDF로 페이지를 이미지로 렌더링한 뒤 EasyOCR로 텍스트 직접 읽음

### OCR을 Docling이 아닌 EasyOCR 직접 사용한 이유
- Docling의 OCR 파이프라인은 텍스트 추출 외에 레이아웃 AI 모델까지 함께 실행 → 또 메모리 부족 에러
- 대신 PyMuPDF로 페이지를 이미지로 변환 → EasyOCR만 직접 호출하는 방식으로 우회
- 페이지를 한 장씩 처리해서 메모리 사용량 최소화 (150 DPI 해상도)

### 결과
- 11개 PDF → data/extracted/*.txt 추출 완료
- 정상 PDF 9개: PyMuPDF로 수초 만에 처리
- 한글 깨진 PDF 2개: EasyOCR로 약 30분 소요

---

## Day 03 · 청크 분할 (chunker.py)

### 왜 청킹이 필요한가?
- 임베딩 모델은 한 번에 처리할 수 있는 텍스트 길이에 제한이 있음 (보통 512토큰 내외)
- 문서 전체를 통째로 넣으면 의미가 뭉개져서 검색 정확도가 떨어짐
- 적당한 크기로 잘라야 나중에 질문과 관련된 부분만 정확히 찾아낼 수 있음

### RecursiveCharacterTextSplitter 선택 이유
- LangChain에서 제공하는 텍스트 분할 도구
- 문단(`\n\n`) → 줄(`\n`) → 문장(`.`) → 단어(` `) → 글자 순서로 자연스러운 경계에서 분할 시도
- 무조건 글자 수로만 자르는 방식보다 문맥이 더 잘 보존됨

### 청킹 전략
- chunk_size = 500: 청크 하나의 최대 글자 수 (이 크기를 넘으면 잘라냄)
- chunk_overlap = 50: 앞 청크와 뒤 청크가 50자씩 겹치게 설정
  - 겹침이 있어야 청크 경계에서 문맥이 잘리는 문제를 줄일 수 있음
  - 예: 청크1의 마지막 50자가 청크2의 시작 부분에도 포함됨

### 결과
- 11개 문서 → 총 1,460개 청크 생성
- 문서별로 data/chunks/*.json 파일로 저장

---

## Day 04 · 임베딩 + ChromaDB 저장 (embedder.py)

### 임베딩이란?
- 텍스트를 숫자 배열(벡터)로 변환하는 것
- 모델 안에는 특정 문장이 저장된 게 아니라 "텍스트를 벡터로 변환하는 규칙"이 학습되어 있음
  → 처음 보는 문장도 즉시 벡터로 변환 가능
- 의미가 비슷한 문장은 비슷한 벡터를 가짐 → 벡터 간 거리를 계산해서 관련 문서 검색 가능

### 모델 선택 이유
- 사용 모델: `snunlp/KR-SBERT-V40K-klueNLI-augSTS`
- 한국어 문장에 특화된 임베딩 모델 (영어 모델 사용 시 한국어 의미를 제대로 못 잡음)
- 벡터 크기: 768차원 (문장 하나 = 768개의 숫자로 표현)

### ChromaDB 구조
- 컬렉션 = 엑셀의 시트 1개 (데이터를 담는 그릇)
- 모든 문서를 한 컬렉션(hr_docs)에 넣은 이유: 검색 시 모든 문서를 동시에 비교해야 하기 때문
- 컬렉션을 나누는 경우: HR문서 / 법무문서 / 재무문서처럼 완전히 다른 서비스를 분리 관리할 때
- 저장 항목:
  - id: 각 청크의 고유 이름 (예: 연차휴가청구권_0)
  - documents: 원본 텍스트
  - embeddings: 768차원 벡터
  - metadatas: 출처 정보 (어느 문서에서 왔는지)

### 트러블슈팅
- 검색 테스트 시 `collection.query(query_texts=["질문"])` 사용
- ChromaDB가 질문을 자기 내장 기본 모델(384차원)로 임베딩해버림
- 저장된 벡터는 KR-SBERT(768차원) → 차원이 달라서 비교 불가 에러 발생
- 해결: 질문도 KR-SBERT로 직접 임베딩한 뒤 `query_embeddings=[벡터]` 로 넘겨야 함
  ```python
  # 에러 난 방식 (ChromaDB가 자기 모델로 임베딩)
  collection.query(query_texts=["연차휴가 며칠 받아요?"])

  # 수정한 방식 (우리가 직접 임베딩해서 전달)
  query_embedding = model.encode("연차휴가 며칠 받아요?").tolist()
  collection.query(query_embeddings=[query_embedding])
  ```

### 결과
- 1,460개 청크 → 768차원 벡터로 변환 완료
- data/vector_store/ 에 ChromaDB 파일로 저장
- DBeaver로 chroma.sqlite3 열어서 1,460개 저장 확인

---

## Day 05 · 유사도 검색 (retriever.py)

### Retriever란?
- 질문을 받아서 ChromaDB에서 가장 관련 있는 청크를 찾아 반환하는 모듈
- RAG 파이프라인에서 "검색" 역할 담당

### 흐름
```
질문 입력
  → KR-SBERT로 질문을 벡터로 변환
  → ChromaDB에서 벡터 거리가 가까운 청크 N개 검색
  → [{"text": "...", "source": "문서명"}, ...] 반환
```

### 트러블슈팅
- 처음엔 질문마다 `SentenceTransformer(MODEL_NAME)` 을 새로 실행
- → `Loading weights` 가 질문마다 반복 출력되고 속도가 느림
- 해결: `_model = None` 전역 변수로 모델을 캐싱
  - 첫 번째 호출 시에만 모델을 로드하고, 이후엔 로드된 모델을 재사용

### 결과
- 3가지 질문 테스트 성공
- 연차휴가 / 육아휴직 / 연말정산 질문 모두 관련 문서에서 청크 반환 확인
- 모델 캐싱 후 두 번째 질문부터 `Loading weights` 미출력 확인

---

## Day 06 · FastAPI /chat 엔드포인트 (main.py, chat.py)

### FastAPI란?
- Python으로 API 서버를 만드는 프레임워크
- 나중에 Streamlit UI가 이 서버에 질문을 보내고 답변을 받아서 화면에 보여줌

### 파일 구조
- `backend/app/main.py`: FastAPI 앱 생성 + 라우터 등록 (진입점)
- `backend/app/api/routes/chat.py`: /chat 엔드포인트 로직 정의
- 라우터를 별도 파일로 분리한 이유: 나중에 /history, /session 등 엔드포인트가 추가될 때 파일별로 관리하기 편하기 때문

### /chat 엔드포인트 동작
1. 클라이언트가 POST /chat `{"question": "연차휴가 며칠?"}` 요청 전송
2. retriever.search() 호출 → ChromaDB에서 관련 청크 3개 검색
3. `{"chunks": [...]}` 형태로 JSON 응답 반환

### 서버 실행 방법
```
uvicorn backend.app.main:app --reload
```
- `--reload`: 코드 수정 시 서버 자동 재시작 (개발 시 편의용)
- `/docs` 접속하면 Swagger UI로 API 테스트 가능

### 결과
- uvicorn 서버 실행 성공 (http://127.0.0.1:8000)
- /docs Swagger UI에서 질문 입력 → 청크 + 출처 반환 확인

---

## Day 07 · 전체 흐름 연결 테스트

### 확인한 전체 파이프라인
```
data/raw/*.pdf          (원본 PDF)
  ↓ parser.py
data/extracted/*.txt    (추출된 텍스트)
  ↓ chunker.py
data/chunks/*.json      (분할된 청크 1,460개)
  ↓ embedder.py
data/vector_store/      (벡터 DB)
  ↓ retriever.py
  ↓ FastAPI /chat
{"chunks": [...]}       (JSON 응답)
```
→ 처음부터 끝까지 에러 없이 연결 확인 ✅

### 발견한 한계 (다음 단계에서 해결 예정)
- 현재는 어떤 질문이든 무조건 ChromaDB 검색만 함
- "졸린데 어카지", "배블러" 같은 문서 무관 질문에도 200 응답으로 청크 반환
- 원인: 라우터가 없어서 질문 종류를 구분하지 않음
- 해결 예정: Day 10에서 LangGraph 라우터 구현
  - 문서 관련 질문 → RAG 검색
  - 일반 질문 → LLM 직접 답변

---

## Day 09 · LangGraph 개념 학습

### LangGraph가 필요한 이유
- 현재 /chat은 질문 종류 상관없이 무조건 RAG 검색만 함
- 문서 관련 질문과 일반 질문을 구분해서 다른 경로로 처리해야 함
- 이 "분기(라우팅) 로직"을 구조적으로 만드는 도구가 LangGraph

### 핵심 개념 3가지

**1. State (상태)**
그래프 전체에서 노드 간에 공유하는 데이터
```python
state = {
    "question": "연차휴가 며칠?",   # 입력 질문
    "route": "rag",                 # 라우터가 결정한 경로
    "chunks": [...],                # RAG 검색 결과
    "answer": "연차휴가는 15일..."  # 최종 답변
}
```

**2. Node (노드)**
실제 작업을 수행하는 함수. State를 받아서 처리하고 업데이트된 State를 반환
- router 노드: 질문이 문서 관련인지 판단
- rag_node: retriever로 문서 검색 후 답변 생성
- llm_node: LLM에 직접 질문해서 답변 생성

**3. Edge (엣지)**
노드 간 연결 경로. 조건에 따라 다른 노드로 분기 가능
- router 결과가 "rag" → rag_node로 이동
- router 결과가 "llm" → llm_node로 이동

### 전체 그래프 구조
```
[START]
   ↓
[router]  ← 질문 분류
   ↓              ↓
[rag_node]    [llm_node]
   ↓              ↓
[END]          [END]
```

---

## Day 10 · LangGraph 구현 (graph.py)

### 구현한 것
- `GraphState`: 노드 간 공유 데이터 구조 (question, route, answer, sources)
- `router()`: LLM이 질문을 보고 "rag" or "llm" 결정
- `rag_node()`: retriever로 문서 검색 → 청크를 컨텍스트로 LLM 답변 생성
- `llm_node()`: 문서 없이 LLM이 직접 답변
- `build_graph()`: 위 노드들을 연결해서 LangGraph 그래프 완성

### 모델 선택 (gpt-4o-mini)
- **라우터**: "rag" or "llm" 둘 중 하나를 고르는 단순 분류 작업 → 고성능 모델 불필요
- **RAG 답변 생성**: 검색된 청크를 받아서 요약하는 작업 → 이미 관련 문서가 컨텍스트로 주어지기 때문에 모델이 복잡한 추론을 할 필요 없음
- **gpt-4o 대비 장점**:
  - 비용: gpt-4o 대비 약 15배 저렴 (포트폴리오 개발 중 API 비용 절약)
  - 속도: 응답 속도가 더 빠름 → 사용자 경험 향상
- **한계**: 매우 복잡한 법령 해석이나 다단계 추론이 필요한 질문은 gpt-4o가 더 정확할 수 있음
  → 추후 답변 품질 개선 시 gpt-4o로 업그레이드 고려 가능

### FastAPI 연결
- 기존 chat.py: `retriever.search()` 직접 호출
- 변경 후: `build_graph().invoke()` 호출
- 응답 구조 변경: `chunks` → `answer + sources + route`

### 테스트 결과
- "나는 오늘 투썸 알바 2시부터 6시까지 일정이 있다"
  → `route: llm` → LLM 직접 답변, sources 없음 ✅
- "나는 아직 입사한지 두달밖에 안되었는데, 연차 없겠지?"
  → `route: rag` → 문서 검색 후 정확한 답변 + 출처 3개 반환 ✅

---

## Day 11 · SQL DB 설계 + 대화 히스토리 저장 (database.py)

### DB 구조
- ChromaDB (`chroma.sqlite3`): 청크 벡터 저장 → 유사도 검색 전용
- SQLite (`chat_history.db`): 대화 내역 저장 → 히스토리 조회 전용
- 역할이 달라서 별도 DB로 분리

### chat_history 테이블 컬럼
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer | 자동 증가 고유 ID |
| question | Text | 사용자 질문 |
| answer | Text | AI 답변 |
| sources | String | 출처 (콤마로 구분, llm이면 빈 값) |
| route | String | rag or llm |
| created_at | DateTime | 저장 시각 |

### 사용 라이브러리
- SQLAlchemy: 파이썬 코드로 DB 조작 (SQL 직접 안 써도 됨)
- aiosqlite: FastAPI 비동기 환경과 SQLite 호환

### 저장 흐름
1. `/chat` 요청 → LangGraph로 답변 생성
2. 질문 + 답변 + 출처 + 경로를 `chat_history` 테이블에 저장
3. DBeaver로 저장 확인 완료

---

## Day 12 · E2E 테스트

### 테스트 결과

| 질문 | route | 결과 |
|------|-------|------|
| "연차휴가 며칠 받을 수 있나요?" | rag | 문서 기반 정확한 답변 ✅ |
| "육아휴직 급여는 얼마예요?" | rag | 문서 기반 정확한 답변 ✅ |
| "입사 3개월인데 연차 있나요?" | rag | 문서 기반 정확한 답변 ✅ |
| "퇴직금은 얼마예요?" | llm | 일반 지식으로 답변 (문서 없음) ✅ |
| "오늘 날씨 어때요?" | llm | 실시간 정보라 API 필요하다고 솔직하게 답변 ✅ |
| "" (빈 질문) | llm | HR 관련 인사말로 자연스럽게 처리 ✅ |

### 발견한 사항
- "퇴직금" 질문이 llm으로 라우팅됨
  - 처음엔 버그처럼 보였지만 퇴직금 관련 문서가 없으므로 llm이 맞는 동작
  - rag로 보내도 관련 청크가 없어서 엉뚱한 답변이 나올 수 있음
- 빈 질문도 에러 없이 처리됨

### 결론
- 전체 파이프라인 정상 동작 확인
- 발견된 버그 없음

---

## Day 13 · Streamlit UI (frontend/app.py)

### Streamlit 선택 이유
- 백엔드가 Python이라 언어 통일 가능
- 코드 몇 줄로 채팅 UI 구현 가능 → 빠른 개발
- AI/데이터 분야 포트폴리오에 적합
- 실서비스 확장 시 React로 전환 가능

### 동작 방식
1. 사용자가 질문 입력
2. Streamlit이 FastAPI `/chat` 으로 POST 요청
3. 답변 + 출처 받아서 화면에 표시
4. `st.session_state` 로 대화 히스토리 유지 (새로고침 전까지)

### 주요 기능
- 채팅 UI (`st.chat_message`, `st.chat_input`)
- 답변 생성 중 로딩 표시 (`st.spinner`)
- 출처가 있을 때만 출처 표시 (llm 경로는 출처 없음)

### 테스트 결과
- "육아휴직 하고싶은데 어떻게 해?" → 문서 기반 답변 + 출처 표시 ✅
- 날짜/날씨 질문 → LLM이 실시간 정보 없다고 솔직하게 답변 ✅

---

## Day 14 · 프롬프트 튜닝 + 대화 히스토리 전달

### 개선한 것

**1. 라우터 프롬프트 개선**
- 기존: HR 키워드 나열만으로 분류
- 변경: 이전 대화 히스토리를 라우터에도 전달
- 효과: "전체적으로 알려줘" 같은 모호한 질문도 이전 맥락(연말정산) 보고 rag로 분류

**2. 대화 히스토리 전달**
- frontend → API → graph 순으로 히스토리 전달
- router / rag_node / llm_node 모두 히스토리 참고
- 효과: 연속 대화에서 맥락 유지

### 트러블슈팅
- `history_messages` 를 `*history_messages` 대신 그냥 넣어서 리스트 안에 리스트가 됨
- LangChain이 메시지 변환 시 에러 발생
- 해결: `*history_messages` 로 언패킹해서 넣어야 함

### 테스트 결과
- "연말정산" → rag, 문서 기반 답변 ✅
- "전체적으로 알려줘" (이전 대화: 연말정산) → rag, 맥락 유지 ✅
- 출처 3개 문서에서 반환 ✅

### RAG 한계 발견 (README 트러블슈팅에 기록 예정)
- "전체적으로 알려줘" 같은 개요 요청은 RAG보다 LLM 직접 답변이 더 풍부함
- RAG는 청크 3개만 참고하기 때문에 개요/전반 설명엔 한계가 있음
- 특정 사실 질문 → RAG 유리 / 개요 설명 → LLM 유리

---

## Day 15 · 코드 리팩토링 + 로깅 추가

### 코드 리팩토링

**graph.py — 중복 코드 제거**
- `router`, `rag_node`, `llm_node` 세 함수가 히스토리 변환 코드를 똑같이 반복하고 있었음
- `_build_history_messages()` 함수로 분리해서 한 곳에서 관리
- 왜 필요한가: 나중에 메시지 변환 방식을 바꿀 때 한 곳만 수정하면 됨

**retriever.py — 하드코딩 상수 분리**
- `n_results=3` → `MAX_SEARCH_RESULTS = 3` 상수로 분리
- 왜 필요한가: 숫자만 보면 왜 3인지 모름. 이름이 있어야 의도가 보임

**chat.py — 에러 핸들링 추가**
- LangGraph 실행 실패 시 → `"답변 생성 중 오류가 발생했습니다"` 메시지 반환
- DB 저장 실패 시 → `rollback()` 후 오류 메시지 반환
- `finally`로 DB 연결이 항상 닫히도록 보장
- 왜 필요한가: 에러 처리 없으면 서버가 500 에러만 뱉고 원인을 알 수 없음

### 로깅 추가 (logger.py)

**왜 로깅이 필요한가**
- "이 질문이 왜 llm으로 갔지?" 같은 상황을 나중에 파악하려면 기록이 있어야 함
- 포트폴리오 발표 시 "모니터링은 어떻게 했나요?" 질문에 답할 수 있음

**구현 방식**
- `backend/app/logger.py` 생성: Python 내장 `logging` 모듈 사용
- 콘솔 + `logs/app.log` 파일 두 곳에 동시 기록
- 서버 재시작 시 핸들러 중복 방지 (`if logger.handlers` 체크)

**로그 출력 예시**
```
# RAG 경로
2026-06-15 14:23:01 | INFO | [ROUTER] route=rag | question=연차휴가는 며칠 받을 수 있나요?
2026-06-15 14:23:03 | INFO | [RAG] sources=['연차휴가.txt'] | answer_len=312

# LLM 경로
2026-06-15 14:23:05 | INFO | [ROUTER] route=llm | question=오늘 점심 뭐 먹지?
2026-06-15 14:23:06 | INFO | [LLM] answer_len=150
```

**로깅 한계 및 판단**
- question + route는 이미 SQLite DB(chat_history 테이블)에 저장되고 있음
- 따라서 logs/app.log 파일 자체는 DB와 중복
- DB에 이미 저장되므로 로그 파일은 실시간 콘솔 확인 용도로만 활용

---

## 트러블슈팅 모음 (README 작성용)

### 1. Docling OOM → PyMuPDF로 전환
- **문제**: PDF → Markdown 변환 라이브러리 Docling 사용 중 OOM(메모리 부족) 에러 발생
- **원인**: Docling이 내부적으로 표 구조 감지 AI 모델(TableFormer, RT-DETR v2)을 실행하는데, 이 모델이 RAM을 과도하게 사용
- **해결**: 문서가 텍스트 중심임을 파악 → PyMuPDF `get_text()` 로 텍스트만 직접 추출하는 방식으로 전환
- **결과**: 메모리 문제 해결, 처리 속도 대폭 향상 (수분 → 수초)

---

### 2. 한글 PDF 인코딩 깨짐 → EasyOCR fallback
- **문제**: 일부 PDF에서 텍스트 추출 시 한글이 아랍/키릴 문자로 깨져서 출력됨
- **원인**: 해당 PDF의 폰트에 ToUnicode 테이블이 없어서 PyMuPDF가 문자를 올바르게 디코딩하지 못함
- **해결**:
  1. 한글 음절(가~힣, 0xAC00~0xD7A3) 비율로 깨진 PDF 자동 감지 (`has_broken_korean()`)
  2. 깨진 PDF는 PyMuPDF로 페이지를 이미지로 렌더링 후 EasyOCR로 텍스트 추출
- **결과**: 11개 PDF 중 2개 OCR 처리 완료, 전체 텍스트 정상 추출

---

### 3. ChromaDB 벡터 차원 불일치 에러
- **문제**: ChromaDB 검색 시 `InvalidArgumentError: Collection expecting embedding with dimension of 768, got 384` 에러 발생
- **원인**: 저장 시 KR-SBERT(768차원)로 임베딩했는데, 검색 시 `query_texts` 를 쓰면 ChromaDB가 자체 내장 모델(384차원)로 임베딩해버림 → 차원 불일치
- **해결**: `query_texts` 대신 `query_embeddings` 사용. 질문도 KR-SBERT로 직접 임베딩해서 전달
- **결과**: 동일 모델로 저장/검색하여 차원 일치, 검색 정상 동작

---

### 4. LangChain 메시지 리스트 중첩 에러
- **문제**: 대화 히스토리 추가 후 `NotImplementedError: Message as a sequence must be (role string, template)` 에러 발생
- **원인**: 메시지 리스트 안에 `history_messages` 를 통째로 넣어서 리스트 안에 리스트가 중첩됨
  ```python
  # 잘못된 방식
  messages = [SystemMessage(...), history_messages, HumanMessage(...)]
  # 올바른 방식
  messages = [SystemMessage(...), *history_messages, HumanMessage(...)]
  ```
- **해결**: `*history_messages` 로 언패킹해서 리스트 항목들을 개별적으로 삽입
- **결과**: 히스토리 메시지 정상 전달, 대화 맥락 유지

---

### 5. RAG의 개요 질문 한계
- **문제**: "전체적으로 알려줘" 같은 개요 요청 시 RAG 답변보다 LLM 직접 답변이 더 풍부함
- **원인**: RAG는 유사도 검색으로 찾은 청크 3개만 참고하기 때문에 전체 개요를 설명하기엔 컨텍스트가 부족함
- **해결**: 현재는 미해결. 라우터가 맥락상 HR 관련 질문으로 판단하면 rag로 보냄
- **개선 방향**: 질문 유형(사실 질문 vs 개요 요청)을 추가로 분류하거나, 청크 수를 늘려 더 많은 컨텍스트 제공 고려
