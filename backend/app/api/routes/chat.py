"""
File    : backend/app/api/routes/chat.py
Author  : 김민정
Create  : 2026-06-14
Description :
    /chat 엔드포인트. 질문을 LangGraph 그래프로 전달하고 답변 + 출처 반환.
    /sessions 엔드포인트. 대화 세션 목록 및 세션별 메시지 반환.

Modification History:
- 2026-06-14 (김민정): 최초 작성.
- 2026-06-15 (김민정): retriever 직접 호출 → LangGraph 그래프로 변경.
- 2026-06-15 (김민정): LangGraph 연결, DB 저장 추가.
- 2026-06-15 (김민정): 대화 히스토리 전달 추가.
- 2026-06-15 (김민정): 에러 핸들링 추가 (LangGraph 실패 시 500 대신 의미있는 메시지 반환).
- 2026-06-16 (김민정): 세션 관리 추가 (ChatGPT처럼 대화별 세션 분리).
"""

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.graph.graph import build_graph
from backend.app.database import SessionLocal, ChatHistory, Session, init_db

# 서버 시작 시 테이블 없으면 생성
init_db()

router = APIRouter()
graph = build_graph()

class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []
    session_id: str | None = None  # 없으면 새 세션 생성

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    route: str
    session_id: str  # 프론트에서 다음 요청에 재사용

class SessionInfo(BaseModel):
    id: str
    title: str
    created_at: str

class MessageItem(BaseModel):
    role: str      # "user" or "assistant"
    content: str
    sources: list[str] = []


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # 질문 → router 판단 → RAG or LLM 선택
    try:
        result = graph.invoke({
            "question": request.question,
            "history": request.history,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 생성 중 오류가 발생했습니다: {str(e)}")

    db = SessionLocal()
    try:
        # 세션이 없으면 새로 생성 (첫 질문을 제목으로 사용)
        session_id = request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            title = request.question[:30] + ("..." if len(request.question) > 30 else "")
            db.add(Session(id=session_id, title=title))

        db.add(ChatHistory(
            session_id=session_id,
            question=request.question,
            answer=result["answer"],
            sources=",".join(result["sources"]),
            route=result["route"],
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"대화 저장 중 오류가 발생했습니다: {str(e)}")
    finally:
        db.close()

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        route=result["route"],
        session_id=session_id,
    )


@router.get("/sessions", response_model=list[SessionInfo])
def get_sessions():
    """최근 대화 세션 목록을 반환 (최신 순)."""
    db = SessionLocal()
    try:
        sessions = db.query(Session).order_by(Session.created_at.desc()).limit(50).all()
        return [
            SessionInfo(id=s.id, title=s.title, created_at=str(s.created_at))
            for s in sessions
        ]
    finally:
        db.close()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageItem])
def get_session_messages(session_id: str):
    """특정 세션의 대화 내역을 [user, assistant, user, assistant, ...] 순으로 반환."""
    db = SessionLocal()
    try:
        histories = (
            db.query(ChatHistory)
            .filter(ChatHistory.session_id == session_id)
            .order_by(ChatHistory.created_at.asc())
            .all()
        )
        messages = []
        for h in histories:
            messages.append(MessageItem(role="user", content=h.question))
            messages.append(MessageItem(
                role="assistant",
                content=h.answer,
                sources=h.sources.split(",") if h.sources else [],
            ))
        return messages
    finally:
        db.close()