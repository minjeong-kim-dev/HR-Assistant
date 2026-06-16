"""
File    : frontend/app.py
Author  : 김민정
Create  : 2026-06-15
Description :
    Streamlit 챗봇 UI. FastAPI /chat 엔드포인트로 질문을 보내고 답변을 화면에 표시.

Modification History:
- 2026-06-15 (김민정): 최초 작성.
- 2026-06-15 (김민정): 대화 히스토리 전달 추가.
- 2026-06-16 (김민정): 멀티 대화 사이드바 추가 (ChatGPT처럼 대화방 전환).
- 2026-06-16 (김민정): 빈 화면 환영 UI + 추천 질문 칩 추가.
"""

import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/chat"
SESSIONS_URL = f"{BASE_URL}/sessions"

st.set_page_config(page_title="HR Assistant", page_icon="💼", layout="wide")

# 추천 질문 칩 버튼 스타일
st.markdown("""
<style>
/* 추천 질문 칩 */
div[data-testid="stHorizontalBlock"] .stButton button {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 20px;
    color: #374151;
    font-size: 0.85rem;
    padding: 6px 16px;
    transition: all 0.15s;
}
div[data-testid="stHorizontalBlock"] .stButton button:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
    color: #111827;
}
</style>
""", unsafe_allow_html=True)


# ── 세션 상태 초기화 ──────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# 추천 칩 클릭 시 저장된 질문
pending_prompt = st.session_state.pop("pending_prompt", None)


def load_session(session_id: str):
    resp = requests.get(f"{SESSIONS_URL}/{session_id}/messages")
    if resp.status_code == 200:
        st.session_state.messages = resp.json()
        st.session_state.session_id = session_id


def start_new_chat():
    st.session_state.messages = []
    st.session_state.session_id = None


# ── 사이드바 ──────────────────────────────────────────────────
with st.sidebar:
    st.title("💼 HR Assistant")

    if st.button("＋  새 대화", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.divider()
    st.caption("이전 대화")

    try:
        sessions_resp = requests.get(SESSIONS_URL, timeout=3)
        sessions = sessions_resp.json() if sessions_resp.status_code == 200 else []
    except Exception:
        sessions = []

    for s in sessions:
        is_current = s["id"] == st.session_state.session_id
        label = ("▶  " if is_current else "") + s["title"]
        if st.button(label, key=s["id"], use_container_width=True):
            load_session(s["id"])
            st.rerun()


# ── 메인 화면 ─────────────────────────────────────────────────
if not st.session_state.messages:
    # 빈 화면: 환영 메시지 + 추천 질문 칩
    st.markdown("<div style='height:18vh'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align:center; font-weight:400; font-size:2rem; color:#111827;'>"
        "준비되면 얘기해 주세요.</h2>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

    _, center, _ = st.columns([1, 3, 1])
    with center:
        chips = [
            ("📅 연차휴가 알아보기", "연차휴가는 며칠 받을 수 있나요?"),
            ("👶 육아휴직 조건",     "육아휴직 신청 조건이 어떻게 되나요?"),
            ("💰 연말정산 공제",     "연말정산 공제 항목이 뭐가 있나요?"),
            ("⏰ 근로시간 규정",     "법정 근로시간은 몇 시간인가요?"),
        ]
        cols = st.columns(len(chips))
        for col, (label, prompt_text) in zip(cols, chips):
            with col:
                if st.button(label, use_container_width=True):
                    st.session_state.pending_prompt = prompt_text
                    st.rerun()

else:
    # 채팅 화면: 대화 내역 출력
    for message in st.session_state.messages:
        avatar = "🙋" if message["role"] == "user" else "📋"
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
            if message.get("sources"):
                st.caption(f"출처: {', '.join(message['sources'])}")


# ── 입력창 (항상 하단 고정) ───────────────────────────────────
typed_prompt = st.chat_input("무엇이든 물어보세요")
final_prompt = typed_prompt or pending_prompt

if final_prompt:
    with st.chat_message("user", avatar="🙋"):
        st.write(final_prompt)
    st.session_state.messages.append({"role": "user", "content": final_prompt})

    with st.chat_message("assistant", avatar="📋"):
        with st.spinner("답변 생성 중..."):
            response = requests.post(API_URL, json={
                "question": final_prompt,
                "history": st.session_state.messages,
                "session_id": st.session_state.session_id,
            })
            result = response.json()

        st.write(result["answer"])
        if result["sources"]:
            st.caption(f"출처: {', '.join(result['sources'])}")

    st.session_state.session_id = result["session_id"]
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })
    st.rerun()
