"""
File    : frontend/app.py
Author  : 김민정
Create  : 2026-06-15
Description :
    Streamlit 챗봇 UI. FastAPI /chat 엔드포인트로 질문을 보내고 답변을 화면에 표시.

Modification History:
- 2026-06-15 (김민정): 최초 작성.
"""

import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/chat"

st.title("HR Assistant")
st.caption("연차휴가, 육아휴직, 연말정산 관련 질문을 해보세요.")

# 대화 히스토리를 세션에 저장
if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 내역 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("sources"):
            st.caption(f"출처: {', '.join(message['sources'])}")

# 질문 입력
prompt = st.chat_input("질문을 입력하세요...")

if prompt:
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # FastAPI 호출
    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            response = requests.post(API_URL, json={"question": prompt})
            result = response.json()

        st.write(result["answer"])
        
        # 출처가 있는 경우
        if result["sources"]:
            st.caption(f"출처: {', '.join(result['sources'])}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
    })
