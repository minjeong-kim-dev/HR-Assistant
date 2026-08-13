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
- 2026-07-06 (김민정): RAG/LLM 메시지 생성 로직을 공통 함수(_build_rag_messages(), _build_llm_messages())로 분리하여 중복 코드 제거.
"""

import os
from typing import TypedDict, Generator
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

def _build_rag_messages(question: str, history: list[dict]):
    """
    RAG용 메시지와 출처를 생성.
    rag_node(), stream_answer()에서 공통으로 사용한다.
    """
    chunks = search(question)
    context = "\n\n".join([c["text"] for c in chunks])
    sources = list(set([c["source"] for c in chunks]))

    history_messages = _build_history_messages(history)

    messages = [
        SystemMessage(content=f"""
            당신은 HR 규정 전문 AI 어시스턴트입니다.
            아래 [참고 문서]를 확인하고 다음 규칙에 따라 답변하세요.

            [규칙]
            - [참고 문서]에 답이 있으면: 문서 내용을 바탕으로 정확하게 답변하세요.
            - [참고 문서]에 답이 없으면: 첫 줄에 반드시 "[문서무관]"을 출력한 뒤, 일반적인 HR·노동법 지식으로 답변하세요.

            예시)
            [문서무관]
            근로계약서는 근로기준법에 따라 반드시 서면으로 작성해야 합니다...

            - 질문이 모호하면 관련 규정을 순서대로 설명해주세요.

            [참고 문서]
            {context}
        """),
        *history_messages,
        HumanMessage(content=question),
    ]

    return messages, sources

def _build_llm_messages(question: str, history: list[dict]):
    history_messages = _build_history_messages(history)

    return [
        SystemMessage(content="당신은 친절한 HR 업무 도우미입니다."),
        *history_messages,
        HumanMessage(content=question),
    ]

def router(state: GraphState) -> GraphState:
    """사용자의 질문을 보고 'rag' 또는 'llm' 경로를 결정."""
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

def route_condition(state: GraphState) -> str:
    """라우터 결과에 따라 다음 노드 결정."""
    return state["route"]

def rag_node(state: GraphState) -> GraphState:
    """문서에서 관련 청크를 검색하고 LLM으로 답변 생성."""
    messages, sources = _build_rag_messages(
        state["question"],
        state.get("history", [])
    )

    response = llm.invoke(messages)
    answer = response.content

    if answer.startswith("[문서무관]"):
        answer = answer.replace("[문서무관]", "").strip()
        sources = []

    logger.info(f"[RAG] sources={sources} | answer_len={len(answer)}")
    
    return {"answer": answer, "sources": sources}


def llm_node(state: GraphState) -> GraphState:
    """문서 없이 LLM이 직접 답변."""
    messages = _build_llm_messages(
        state["question"],
        state.get("history", [])
    )

    response = llm.invoke(messages)
    logger.info(f"[LLM] answer_len={len(response.content)}")

    return {
        "answer": response.content,
        "sources": []
    }

def stream_answer(question: str, history: list[dict]) -> Generator:
    """
    라우팅 후 LLM 답변을 토큰 단위로 yield.
    마지막에 메타데이터 dict {"answer", "sources", "route"} 를 yield.
    """
    # 1. 라우팅 (비스트리밍 - 빠른 분류)
    router_result = router({"question": question, "history": history, "route": "", "answer": "", "sources": []})
    route = router_result["route"]

    # 2. 메시지 구성
    if route == "rag":
        messages, sources = _build_rag_messages(question, history)
    else:
        messages = _build_llm_messages(question, history)
        sources = []

    # 3. 토큰 스트리밍 + [문서무관] 처리
    PREFIX = "[문서무관]"
    buffer = ""
    full_answer = ""
    prefix_checked = False

    for chunk in llm.stream(messages):
        token = chunk.content
        if not token:
            continue
        full_answer += token

        if not prefix_checked:
            buffer += token
            if len(buffer) >= len(PREFIX):
                prefix_checked = True
                if buffer.startswith(PREFIX):
                    sources = []
                    rest = buffer[len(PREFIX):].lstrip()
                    if rest:
                        yield rest
                else:
                    yield buffer
                buffer = ""
        else:
            yield token

    # 버퍼에 남은 내용 처리 (답변이 PREFIX보다 짧은 경우)
    if buffer:
        if buffer.startswith(PREFIX):
            sources = []
        else:
            yield buffer

    if full_answer.startswith(PREFIX):
        full_answer = full_answer[len(PREFIX):].strip()
        sources = []

    logger.info(f"[STREAM] route={route} | sources={sources} | answer_len={len(full_answer)}")
    yield {"answer": full_answer, "sources": sources, "route": route}


def build_graph():
    """LangGraph 그래프 생성."""
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
