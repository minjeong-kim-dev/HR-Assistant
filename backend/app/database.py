"""
File    : backend/app/database.py
Author  : 김민정
Create  : 2026-06-15
Description :
    SQLite DB 연결 설정 및 테이블 정의.
    대화 히스토리(질문, 답변, 출처, 경로)를 저장.

Modification History:
- 2026-06-15 (김민정): 최초 작성.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# SQLite 파일로 저장 (data/chat_history.db)
DATABASE_URL = "sqlite:///data/chat_history.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ChatHistory(Base):
    """
    대화 히스토리 테이블.
    """
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)             # 사용자 질문
    answer = Column(Text, nullable=False)               # AI 답변
    sources = Column(String, nullable=True)             # 출처 (콤마로 구분)
    route = Column(String, nullable=True)               # rag or llm
    created_at = Column(DateTime, default=datetime.now) # 저장 시각


def init_db():
    """테이블이 없으면 생성."""
    Base.metadata.create_all(bind=engine)
