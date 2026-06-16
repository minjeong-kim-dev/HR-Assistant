"""
File    : backend/app/database.py
Author  : 김민정
Create  : 2026-06-15
Description :
    SQLite DB 연결 설정 및 테이블 정의.
    대화 히스토리(질문, 답변, 출처, 경로)를 저장.

Modification History:
- 2026-06-15 (김민정): 최초 작성.
- 2026-06-16 (김민정): Session 테이블 추가, ChatHistory에 session_id 컬럼 추가.
"""

import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# SQLite 파일로 저장 (data/chat_history.db)
DATABASE_URL = "sqlite:///data/chat_history.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Session(Base):
    """
    대화 세션 테이블. 각 대화방 1개 = 세션 1개.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)               # 첫 질문을 제목으로 사용
    created_at = Column(DateTime, default=datetime.now)


class ChatHistory(Base):
    """
    대화 히스토리 테이블.
    """
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=True)           # 어느 세션에 속하는지
    question = Column(Text, nullable=False)              # 사용자 질문
    answer = Column(Text, nullable=False)                # AI 답변
    sources = Column(String, nullable=True)              # 출처 (콤마로 구분)
    route = Column(String, nullable=True)                # rag or llm
    created_at = Column(DateTime, default=datetime.now)  # 저장 시각


def init_db():
    """테이블이 없으면 생성. 기존 테이블에 session_id 컬럼이 없으면 추가."""
    Base.metadata.create_all(bind=engine)
    # 기존 chat_history 테이블에 session_id 컬럼이 없을 경우 추가 (SQLite는 ALTER TABLE만 가능)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_id TEXT"))
            conn.commit()
        except Exception:
            pass  # 이미 컬럼이 있으면 무시
