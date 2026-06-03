# Taxbot Folder Structure

이 문서는 현재 `taxbot` 프로젝트의 폴더 구조와 각 폴더의 역할을 정리한 파일입니다.

```text
taxbot/
├─ frontend/                              # React 프론트엔드
│  ├─ src/                                # 화면 컴포넌트, 페이지, 상태 관리
│  └─ public/                             # 정적 자산
│
├─ backend/                               # FastAPI 백엔드
│  └─ app/                                # 실제 서버 애플리케이션 코드
│     ├─ api/                             # API 엔드포인트
│     │  └─ routes/                       # 라우트 파일 모음
│     │     ├─ chat.py                    # 채팅 질의응답 API
│     │     └─ health.py                  # 서버 상태 확인 API
│     │
│     ├─ graph/                           # LangGraph 워크플로우
│     │  ├─ router.py                     # 질문 유형 분류
│     │  ├─ nodes.py                      # 각 노드 정의
│     │  └─ workflow.py                   # 전체 그래프 연결
│     │
│     ├─ rag/                             # RAG 관련 로직
│     │  ├─ parser.py                     # PDF -> Markdown 변환
│     │  ├─ chunker.py                    # Markdown -> Chunk 분할
│     │  ├─ embeddings.py                 # 임베딩 생성
│     │  ├─ vector_store.py               # ChromaDB 저장/조회
│     │  └─ retriever.py                  # 유사 문서 검색
│     │
│     ├─ services/                        # API와 RAG 사이 비즈니스 로직
│     └─ utils/                           # 공통 유틸 함수
│
├─ data/                                  # 프로젝트 데이터 저장소
│  ├─ raw/                                # 원본 PDF 파일
│  ├─ markdown/                           # Docling 변환 결과(.md)
│  ├─ chunks/                             # Chunking 결과
│  └─ vector_store/                       # ChromaDB 저장소
│
└─ docs/                                  # 프로젝트 문서
```

## 현재 이동된 파일

<!-- 원본 PDF는 모두 `data/raw/`로 이동했습니다. -->
- `data/raw/(260203)수정사항.pdf`
- `data/raw/근로시간_연차유급휴가_행정해석.pdf`
- `data/raw/근로시간_주휴수당및연차산정.pdf`
- `data/raw/연말정산_신고안내_2025.pdf`
- `data/raw/연말정산_주택자금및월세공제_2025.pdf`
- `data/raw/연말정산_중소기업취업자소득세감면_2025.pdf`
- `data/raw/연차휴가_1년미만근로자_연차확대.pdf`
- `data/raw/연차휴가_사용촉진_QA.pdf`
- `data/raw/연차휴가_사용촉진제도.pdf`
- `data/raw/연차휴가청구권.pdf`
- `data/raw/육아휴직_사용안내서_2024.pdf`

## 메모

<!-- 이 구조는 PDF 기반 RAG 파이프라인을 기준으로 나눈 것입니다. -->
- `frontend`는 사용자 화면을 담당합니다.
- `backend/app/rag`는 문서 변환과 검색 로직을 담당합니다.
- `data`는 원본과 중간 산출물을 구분해서 보관합니다.
