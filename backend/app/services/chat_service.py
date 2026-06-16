"""
File    : backend/app/services/chat_service.py
Author  : 김민정
Create  : 2026-06-16
Description :
    /chat, /sessions 관련 비즈니스 로직.
    LangGraph 호출, 세션 생성, DB 저장을 담당.
    HTTP 레이어(routes)와 분리하여 각 계층이 하나의 역할만 갖도록 함.
"""

import uuid
import json
from backend.app.graph.graph import build_graph, stream_answer
from backend.app.database import SessionLocal, ChatHistory, Session, init_db

# 서버 시작 시 테이블 없으면 생성 + 그래프는 한 번만 빌드 (재사용)
init_db()
graph = build_graph()


def process_chat(question: str, history: list[dict], session_id: str | None) -> dict:
    """
    질문을 LangGraph로 처리하고 결과를 DB에 저장 후 반환.

    Args:
        question: 사용자 질문
        history: 이전 대화 목록 [{"role": "user"/"assistant", "content": "..."}]
        session_id: 기존 세션 ID (없으면 새 세션 생성)

    Returns:
        {"answer": str, "sources": list, "route": str, "session_id": str}
    """
    # 1. LangGraph 실행 (router → rag_node or llm_node)
    try:
        result = graph.invoke({"question": question, "history": history})
    except Exception as e:
        raise RuntimeError(f"답변 생성 중 오류가 발생했습니다: {str(e)}")

    # 2. 세션 생성 + 대화 내역 DB 저장
    db = SessionLocal()
    try:
        if not session_id:
            session_id = str(uuid.uuid4())
            title = question[:30] + ("..." if len(question) > 30 else "")
            db.add(Session(id=session_id, title=title))

        db.add(ChatHistory(
            session_id=session_id,
            question=question,
            answer=result["answer"],
            sources=",".join(result["sources"]),
            route=result["route"],
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"대화 저장 중 오류가 발생했습니다: {str(e)}")
    finally:
        db.close()

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "route": result["route"],
        "session_id": session_id,
    }


def fetch_sessions() -> list[dict]:
    """세션 목록을 최신순으로 반환."""
    db = SessionLocal()
    try:
        sessions = db.query(Session).order_by(Session.created_at.desc()).limit(50).all()
        return [
            {"id": s.id, "title": s.title, "created_at": str(s.created_at)}
            for s in sessions
        ]
    finally:
        db.close()


def delete_session(session_id: str) -> None:
    """세션과 해당 세션의 대화 내역을 DB에서 삭제."""
    db = SessionLocal()
    try:
        db.query(ChatHistory).filter(ChatHistory.session_id == session_id).delete()
        db.query(Session).filter(Session.id == session_id).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"세션 삭제 중 오류가 발생했습니다: {str(e)}")
    finally:
        db.close()


def fetch_session_messages(session_id: str) -> list[dict]:
    """특정 세션의 대화 내역을 [user, assistant, ...] 순으로 반환."""
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
            messages.append({"role": "user", "content": h.question, "sources": []})
            messages.append({
                "role": "assistant",
                "content": h.answer,
                "sources": h.sources.split(",") if h.sources else [],
            })
        return messages
    finally:
        db.close()


def stream_chat(question: str, history: list[dict], session_id: str | None):
    """
    스트리밍 답변 생성 후 DB 저장. FastAPI StreamingResponse에 전달하는 SSE 문자열 generator.
    - str yield: 'data: {"type":"token","content":"..."}\\n\\n'
    - 마지막: 'data: {"type":"done","session_id":"...","sources":[...]}\\n\\n'
    """
    meta = None

    for item in stream_answer(question, history):
        if isinstance(item, dict):
            meta = item
        else:
            yield f"data: {json.dumps({'type': 'token', 'content': item}, ensure_ascii=False)}\n\n"

    # DB 저장
    if meta:
        db = SessionLocal()
        try:
            if not session_id:
                session_id = str(uuid.uuid4())
                title = question[:30] + ("..." if len(question) > 30 else "")
                db.add(Session(id=session_id, title=title))
            db.add(ChatHistory(
                session_id=session_id,
                question=question,
                answer=meta["answer"],
                sources=",".join(meta["sources"]),
                route=meta["route"],
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    sources = meta["sources"] if meta else []
    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': sources}, ensure_ascii=False)}\n\n"
