"""
File    : backend/app/api/routes/chat.py
Author  : 김민정
Create  : 2026-06-14
Description :
    /chat 엔드포인트. 질문을 받아 retriever로 검색 후 관련 청크를 반환.

Modification History:
- 2026-06-14 (김민정): 최초 작성.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.rag.retriever import search

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    chunks: list[dict]

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    results = search(request.question)

    return ChatResponse(chunks=results)