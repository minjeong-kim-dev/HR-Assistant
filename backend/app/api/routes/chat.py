"""
File    : backend/app/api/routes/chat.py
Author  : 김민정
Create  : 2026-06-14
Description :
    /chat 엔드포인트. 질문을 LangGraph 그래프로 전달하고 답변 + 출처 반환.

Modification History:
- 2026-06-14 (김민정): 최초 작성.
- 2026-06-15 (김민정): retriever 직접 호출 → LangGraph 그래프로 변경.
- 2026-06-15 (김민정): LangGraph 연결, DB 저장 추가.
- 2026-06-15 (김민정): 대화 히스토리 전달 추가.
- 2026-06-15 (김민정): 에러 핸들링 추가 (LangGraph 실패 시 500 대신 의미있는 메시지 반환).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.graph.graph import build_graph
from backend.app.database import SessionLocal, ChatHistory, init_db

# 서버 시작 시 테이블 없으면 생성
init_db()  

router = APIRouter()
graph = build_graph()

class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    route: str

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

    # DB에 대화 내역 저장
    db = SessionLocal()
    try:
        db.add(ChatHistory(
            question=request.question,
            answer=result["answer"],
            # DB는 리스트를 직접 저장하지 못하여 문자열로 변환 후 저장
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
    )