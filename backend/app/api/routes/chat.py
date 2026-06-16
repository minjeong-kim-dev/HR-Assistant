"""
File    : backend/app/api/routes/chat.py
Author  : 김민정
Create  : 2026-06-14
Description :
    /chat, /sessions 엔드포인트 정의.
    HTTP 요청 수신 → chat_service 호출 → HTTP 응답 반환만 담당.
    비즈니스 로직은 backend/app/services/chat_service.py 에 위임.

Modification History:
- 2026-06-14 (김민정): 최초 작성.
- 2026-06-15 (김민정): retriever 직접 호출 → LangGraph 그래프로 변경.
- 2026-06-15 (김민정): LangGraph 연결, DB 저장 추가.
- 2026-06-15 (김민정): 대화 히스토리 전달 추가.
- 2026-06-15 (김민정): 에러 핸들링 추가 (LangGraph 실패 시 500 대신 의미있는 메시지 반환).
- 2026-06-16 (김민정): 세션 관리 추가 (ChatGPT처럼 대화별 세션 분리).
- 2026-06-16 (김민정): 비즈니스 로직을 chat_service.py 로 분리.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.app.services.chat_service import process_chat, fetch_sessions, fetch_session_messages, delete_session, stream_chat

router = APIRouter()


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
    role: str       # "user" or "assistant"
    content: str
    sources: list[str] = []


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = process_chat(request.question, request.history, request.session_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(**result)


@router.get("/sessions", response_model=list[SessionInfo])
def get_sessions():
    try:
        return fetch_sessions()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=list[MessageItem])
def get_session_messages(session_id: str):
    try:
        return fetch_session_messages(session_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    try:
        delete_session(session_id)
        return {"message": "삭제 완료"}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_chat(request.question, request.history, request.session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
