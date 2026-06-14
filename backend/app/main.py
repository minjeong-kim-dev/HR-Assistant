"""
File    : backend/app/main.py
Author  : 김민정
Create  : 2026-06-14
Description :
    FastAPI 앱 진입점. 라우터 등록 및 서버 실행.

Modification History:
- 2026-06-14 (김민정): 최초 작성.
"""
from fastapi import FastAPI
from backend.app.api.routes.chat import router

app = FastAPI(title="HR Assistant API")
app.include_router(router)
