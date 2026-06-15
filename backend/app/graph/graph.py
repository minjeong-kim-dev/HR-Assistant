"""
File    : backend/app/graph/graph.py
Author  : 김민정
Create  : 2026-06-15
Description :
    LangGraph로 질문 라우팅 + RAG/LLM 답변 생성 그래프 구현.
    문서 관련 질문 → RAG 노드, 일반 질문 → LLM 노드로 분기.

Modification History:
- 2026-06-15 (김민정): 최초 작성.
"""

import os
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.app.rag.retriever import search

load_dotenv()

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0)


# 노드 간 공유할 데이터 구조 정의
class GraphState(TypedDict):
    question: str
    route: str
    answer: str
    sources: list[str]


def router(state: GraphState) -> GraphState:
    """
    사용자의 질문을 보고 'rag' 또는 'llm' 경로를 결정.
    """

    messages = [
        SystemMessage(content="""
            당신은 질문을 분류하는 라우터입니다.
            질문이 연차휴가, 육아휴직, 연말정산, 근로시간 등 HR/인사 문서와 관련된 경우 'rag'를 반환하세요.
            그 외 일반적인 질문은 'llm'을 반환하세요.
            반드시 'rag' 또는 'llm' 중 하나만 반환하세요.
        """),
        HumanMessage(content=state["question"]),
    ]
    response = llm.invoke(messages)
    route = response.content.strip().lower()

    if route not in ("rag", "llm"):
        # rag/llm이 아닌 겂을 반환할 경우 llm으로 강제 변환
        route = "llm"

    return {"route": route}


def rag_node(state: GraphState) -> GraphState:
    """
    문서에서 관련 청크를 검색하고 LLM으로 답변 생성.
    """

    chunks = search(state["question"])
    context = "\n\n".join([c["text"] for c in chunks])
    sources = list(set([c["source"] for c in chunks]))

    messages = [
        SystemMessage(content=f"""
            아래 문서를 참고해서 질문에 답하세요.
            문서에 없는 내용은 답하지 마세요.

            [참고 문서]
            {context}
        """),
        HumanMessage(content=state["question"]),
    ]
    response = llm.invoke(messages)
    
    return {"answer": response.content, "sources": sources}


def llm_node(state: GraphState) -> GraphState:
    """
    문서 없이 LLM이 직접 답변.
    """
    messages = [
        SystemMessage(content="당신은 친절한 HR 업무 도우미입니다."),
        HumanMessage(content=state["question"]),
    ]
    response = llm.invoke(messages)

    return {"answer": response.content, "sources": []}


def route_condition(state: GraphState) -> str:
    """
    라우터 결과에 따라 다음 노드 결정.
    """
    return state["route"]


def build_graph():
    """
    LangGraph 그래프 생성.
    """
    graph = StateGraph(GraphState)

    graph.add_node("router", router)
    graph.add_node("rag_node", rag_node)
    graph.add_node("llm_node", llm_node)

    # 항상 router 부터 시작
    graph.set_entry_point("router")
    graph.add_conditional_edges("router", route_condition, {
        "rag": "rag_node",  # router 가 "rag" 반환 → rag_node 
        "llm": "llm_node",  # router 가 "llm" 반환 → llm_node
    })
    graph.add_edge("rag_node", END)
    graph.add_edge("llm_node", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    questions = [
        "연차휴가는 며칠 받을 수 있나요?",
        "오늘 점심 뭐 먹지?",
    ]

    for question in questions:
        result = app.invoke({"question": question})
        print(f"\n질문: {question}")
        print(f"경로: {result['route']}")
        print(f"답변: {result['answer'][:200]}")
        print("-" * 40)
