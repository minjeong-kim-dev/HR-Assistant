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
- 2026-06-16 (김민정): 대화 삭제 기능 추가 (hover 시 버튼 표시 + 팝업 확인).
"""

import json
import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/chat"
STREAM_URL = f"{BASE_URL}/chat/stream"
SESSIONS_URL = f"{BASE_URL}/sessions"

st.set_page_config(page_title="HR Assistant", page_icon="💼", layout="wide")

st.markdown("""
<style>
/* 추천 질문 칩 (메인 영역 한정) */
.main [data-testid="stHorizontalBlock"] .stButton button {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 20px;
    color: #374151;
    font-size: 0.85rem;
    padding: 6px 16px;
    transition: all 0.15s;
}
.main [data-testid="stHorizontalBlock"] .stButton button:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
    color: #111827;
}

/* 사이드바 삭제 버튼: 기본 숨김 */
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:nth-child(2) {
    flex: 0 0 auto !important;
    width: 2rem !important;
    min-width: 2rem !important;
}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:nth-child(2) button {
    opacity: 0;
    transition: opacity 0.15s;
    background: transparent !important;
    border: none !important;
    color: #9CA3AF !important;
    box-shadow: none !important;
    font-size: 1.4rem !important;
    padding: 0 !important;
    width: 2rem !important;
    min-width: 2rem !important;
}
/* 세션 행에 마우스 올리면 삭제 버튼 표시 */
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:hover > div:nth-child(2) button {
    opacity: 1;
    color: #EF4444 !important;
}
</style>
""", unsafe_allow_html=True)


# ── 세션 상태 초기화 ──────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None

pending_prompt = st.session_state.pop("pending_prompt", None)


def load_session(session_id: str):
    resp = requests.get(f"{SESSIONS_URL}/{session_id}/messages")
    if resp.status_code == 200:
        st.session_state.messages = resp.json()
        st.session_state.session_id = session_id


def start_new_chat():
    st.session_state.messages = []
    st.session_state.session_id = None


def remove_session(session_id: str) -> bool:
    try:
        resp = requests.delete(f"{SESSIONS_URL}/{session_id}", timeout=5)
        resp.raise_for_status()
    except Exception as e:
        st.error(f"삭제 실패: {e}")
        return False
    if st.session_state.session_id == session_id:
        start_new_chat()
    return True


@st.dialog("대화 삭제")
def confirm_delete_dialog():
    st.write("정말 삭제하시겠습니까?")
    st.caption("삭제하면 모든 내역이 완전히 사라집니다.")
    c1, c2 = st.columns(2)
    if c1.button("삭제", type="primary", use_container_width=True):
        if remove_session(st.session_state.pending_delete):
            st.session_state.pending_delete = None
            st.rerun()
    if c2.button("취소", use_container_width=True):
        st.session_state.pending_delete = None
        st.rerun()


# 삭제 확인 팝업 표시
if st.session_state.pending_delete:
    confirm_delete_dialog()


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
        col_title, col_del = st.columns([5, 0.6])
        with col_title:
            if st.button(label, key=s["id"], use_container_width=True):
                load_session(s["id"])
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{s['id']}"):
                st.session_state.pending_delete = s["id"]
                st.rerun()


# ── 메인 화면 ─────────────────────────────────────────────────
if not st.session_state.messages:
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

    meta = {}

    def token_stream():
        with requests.post(
            STREAM_URL,
            json={
                "question": final_prompt,
                "history": st.session_state.messages,
                "session_id": st.session_state.session_id,
            },
            stream=True,
            timeout=60,
        ) as resp:
            for line in resp.iter_lines():
                if line and line.startswith(b"data: "):
                    data = json.loads(line[6:])
                    if data["type"] == "token":
                        yield data["content"]
                    elif data["type"] == "done":
                        meta.update(data)

    with st.chat_message("assistant", avatar="📋"):
        loading = st.empty()
        loading.markdown("*답변 생성 중...*")

        def wrapped_stream():
            first = True
            for token in token_stream():
                if first:
                    loading.empty()  # 첫 토큰 도착 시 로딩 표시 제거
                    first = False
                yield token

        answer = st.write_stream(wrapped_stream())
        if meta.get("sources"):
            st.caption(f"출처: {', '.join(meta['sources'])}")

    st.session_state.session_id = meta.get("session_id")
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": meta.get("sources", []),
    })
    st.rerun()
