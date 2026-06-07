## 나에 대해
- AI 에이전트 개발자 신입 준비 중
- 현재 입사지원서 및 포트폴리오 작성 중
- 계획 세우고 지키는 것을 어려워함 → 오늘 할 일, 우선순위 1개, 시간 배분을 항상 명확하게 알려줄 것
- 부트 캠프에서 진행한 팀프로젝트가 3개 있지만, 프로젝트 이해도가 낮아 개인 프로젝트로 역량을 강화할 예정
- 프로젝트 전체를 깊이 이해하는 것이 목표 → 코드만 주지 말고 "왜 이렇게 하는지" 항상 설명할 것

## 프로젝트 목표
기업 인사·행정 규정 문서를 기반으로 자연어 질의응답 및 출처 기반 답변을 제공하는 업무 지원 AI Assistant
- 문서수집 : 연말정산/육아휴직/연차휴가/근로시간.휴게시간.휴일 pdf
- 문서 관련 질문 → RAG로 벡터DB 검색 후 답변 + 출처 표시
- 문서에 없는 일반 질문 → LLM 직접 답변
- LangGraph로 두 가지 경로를 라우팅

## 기술 스택
- Language: Python
- Agent Framework: LangChain, LangGraph
- API Server: FastAPI
- Vector DB: ChromaDB
- DB: SQL (대화 히스토리 / 세션 저장)
- UI: Streamlit
- RAG 파이프라인 직접 구현

## 아키텍처 요약
PDF → Markdown 변환
  → 청크 분할 + 임베딩
  → ChromaDB 저장
  → LangGraph Agent (문서 질문 / 일반 질문 라우팅)
  → FastAPI 서버
  → Streamlit UI
SQL DB → 대화 히스토리 / 세션 저장

## 코드 작업 시 원칙
- 코드 먼저 치지 말고 "왜 이게 필요한가" 1줄 적고 시작
- 초보자도 이해할 수 있도록 주석 포함
- 단계별로 설명하면서 진행
- 포트폴리오용이므로 코드 구조와 가독성 중요
- 매일 커밋 1개 (커밋 메시지가 일기장)
- 막히면 하루 넘기지 않기 → 바로 /prioritize 로 재조정
- 완성 > 완벽. Day 20까지 E2E가 돌아가는 게 진짜 목표


## 프로젝트 진행 방식
- 30일 안에 완성 목표
- 계획 세우고 지키는 것을 어려워함
  → 오늘 할 일, 우선순위 1개, 시간 배분을 항상 명확하게 알려줄 것
- 프로젝트 전체를 깊이 이해하는 것이 목표
  → 코드만 주지 말고 "왜 이렇게 하는지" 항상 설명할 것
- 모든 기술 선택에는 비즈니스 근거가 있어야 함
  → 예: NotebookLM의 불편함을 개선하는 것이 이 프로젝트의 존재 이유

## 30일 로드맵
- Phase 1 · 기반 (Day 1–8)
    - Day 1: 환경 세팅 & 프로젝트 구조 설계
    - Day 2: PDF → Markdown 변환 파이프라인
    - Day 3: 청크 분할 전략 이해 + 구현
    - Day 4: 임베딩 모델 이해 + ChromaDB 저장
    - Day 5: ChromaDB 유사도 검색 테스트
    - Day 6: FastAPI 기본 구조 + /chat 엔드포인트 skeleton
    - Day 7: 전체 흐름 연결 테스트 (PDF→검색→API)
    - Day 8: 버퍼 & Phase 1 회고

- Phase 2 · 핵심 (Day 9–20)
    - Day 9: LangGraph 개념 학습 (State, Node, Edge)
    - Day 10: 라우터 노드 구현 (문서 vs 일반 질문 분류)
    - Day 11: RAG 체인 구현 (검색 → 프롬프트 → 답변)
    - Day 12: 일반 질문 LLM 직접 답변 노드
    - Day 13: LangGraph 전체 그래프 연결
    - Day 14: 출처(source) 표시 기능 추가
    - Day 15: SQL DB 설계 (세션/히스토리 테이블)
    - Day 16: 대화 히스토리 저장 & 불러오기
    - Day 17: FastAPI ↔ LangGraph 완전 연결
    - Day 18: E2E 테스트 + 버그 목록 작성
    - Day 19: 버그 수정 1차
    - Day 20: 버퍼 & Phase 2 회고

- Phase 3 · 완성도 (Day 21–27)
    - Day 21: 프롬프트 튜닝 (답변 품질 개선)
    - Day 22: 챗봇 UI (Streamlit)
    - Day 23: 에러 핸들링 & 엣지 케이스 처리
    - Day 24: 로깅 추가 (어떤 경로로 답했는지 기록)
    - Day 25: 코드 리팩토링 + 주석 정비
    - Day 26: README + 아키텍처 다이어그램 완성
    - Day 27: 실제 PDF 4종으로 최종 QA

- Phase 4 · 포트폴리오 (Day 28–30)
    - Day 28: 포트폴리오 문서 작성 (기술 선택 이유, 트러블슈팅)
    - Day 29: 발표 흐름 정리 + 예상 면접 질문 준비
    - Day 30: 데모 시연 연습 + 최종 제출

## 진행 현황
완료한 날: 0 / 30일
오늘 날짜: Day 1
최근 완료 작업

Claude Code 설치 완료
CLAUDE.md 세팅 완료

현재 막히는 부분
(없음)

## 명령어
- 계획 & 관리
    - /plan — 오늘 할 일 (범위 명확하게)
    - /prioritize — 오늘 우선순위 1개 + 예상 소요시간
    - /timeblock — 지금 당장 N시간 집중 계획
    - /roadmap — 30일 전체 일정 확인/수정
    - /review — 오늘 or 주간 회고

- 프로젝트 이해
    - /explain — 이 기술/코드가 왜 필요한지 설명
    - /eli5 — 아주 쉽게 설명
    - /firstprinciples — 기본 원리부터
    - /teach — 내가 설명해보고 이해도 확인

- 비즈니스 전략
    - /validate — 이 프로젝트의 존재 이유 정리
    - /usp — 내 프로젝트 강점
    - /positioning — NotebookLM 대비 차별점
    - /proscons — 기술 선택 장단점

- 코딩
    - /pseudocode — 로직 먼저 작성
    - /stepbystep — 단계별 설명
    - /debug — 버그 찾기
    - /refactor — 코드 정리
    - /review — 코드 리뷰
    - /blueprint — 실행 설계안