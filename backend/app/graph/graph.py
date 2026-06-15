"""
File    : backend/app/graph/graph.py
Author  : 김민정
Create  : 2026-06-15
Description :
    LangGraph로 질문 라우팅 + RAG/LLM 답변 생성 그래프 구현.
    문서 관련 질문 → RAG 노드, 일반 질문 → LLM 노드로 분기.

Modification History:
- 2026-06-15 (김민정): 최초 작성.
- 2026-06-15 (김민정): 대화 히스토리 전달 추가.
- 2026-06-15 (김민정): 중복 히스토리 변환 코드 _build_history_messages() 함수로 분리.
"""

import os
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.app.rag.retriever import search
from backend.app.logger import logger

load_dotenv()

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0)


# 노드 간 공유할 데이터 구조 정의
class GraphState(TypedDict):
    question: str
    route: str
    answer: str
    sources: list[str]
    history: list[dict]


def _build_history_messages(history: list[dict]) -> list:
    """대화 히스토리(dict 리스트)를 LangChain 메시지 객체 리스트로 변환."""
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(SystemMessage(content=msg["content"]))
    return messages


def router(state: GraphState) -> GraphState:
    """
    사용자의 질문을 보고 'rag' 또는 'llm' 경로를 결정.
    """
    history_messages = _build_history_messages(state.get("history", []))

    messages = [
        SystemMessage(content="""
            당신은 질문을 분류하는 라우터입니다.
            아래 주제와 조금이라도 관련이 있으면 'rag'를 반환하세요.
            이전 대화 맥락을 고려해서 판단하세요.
            - 연차휴가, 연차, 휴가, 휴일
            - 육아휴직, 출산휴가, 육아
            - 연말정산, 세금, 공제, 환급
            - 근로시간, 주휴수당, 초과근무

            위 주제와 전혀 관련 없는 일상 질문은 'llm'을 반환하세요.
            반드시 'rag' 또는 'llm' 중 하나만 반환하세요.
        """),
        *history_messages,
        HumanMessage(content=state["question"]),
    ]
    response = llm.invoke(messages)
    route = response.content.strip().lower()

    if route not in ("rag", "llm"):
        # rag/llm이 아닌 값을 반환할 경우 llm으로 강제 변환
        route = "llm"

    logger.info(f"[ROUTER] route={route} | question={state['question'][:50]}")
    return {"route": route}


def rag_node(state: GraphState) -> GraphState:
    """
    문서에서 관련 청크를 검색하고 LLM으로 답변 생성.
    """

    chunks = search(state["question"])
    context = "\n\n".join([c["text"] for c in chunks])
    sources = list(set([c["source"] for c in chunks]))

    history_messages = _build_history_messages(state.get("history", []))

    messages = [
        SystemMessage(content=f"""
            아래 [참고 문서]에 있는 내용만을 사용하여 질문에 답하세요.
            반드시 문서에 명시된 내용만 답하고, 문서에 없는 내용은 절대 추가하지 마세요.
            질문이 모호하거나 "처음인데", "잘 모르는데" 같은 표현이 있으면 관련 내용을 순서대로 설명해주세요.

            [참고 문서]
            {context}
        """),
        *history_messages,
        HumanMessage(content=state["question"]),
    ]
    response = llm.invoke(messages)

    logger.info(f"[RAG] sources={sources} | answer_len={len(response.content)}")
    return {"answer": response.content, "sources": sources}


def llm_node(state: GraphState) -> GraphState:
    """
    문서 없이 LLM이 직접 답변.
    """
    history_messages = _build_history_messages(state.get("history", []))

    messages = [
        SystemMessage(content="당신은 친절한 HR 업무 도우미입니다."),
        *history_messages,
        HumanMessage(content=state["question"]),
    ]
    response = llm.invoke(messages)

    logger.info(f"[LLM] answer_len={len(response.content)}")
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
