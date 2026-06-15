"""
File    : backend/app/api/routes/chat.py
Author  : 김민정
Create  : 2026-06-14
Description :
    /chat 엔드포인트. 질문을 LangGraph 그래프로 전달하고 답변 + 출처 반환.

Modification History:
- 2026-06-14 (김민정): 최초 작성.
- 2026-06-15 (김민정): retriever 직접 호출 → LangGraph 그래프로 변경.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.graph.graph import build_graph

router = APIRouter()
graph = build_graph()

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    route: str

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # 질문 → router 판단 → RAG or LLM 선택
    result = graph.invoke({"question": request.question})

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        route=result["route"],
    )
