"""
File    : backend/app/logger.py
Author  : 김민정
Create  : 2026-06-15
Description :
    앱 전체에서 사용할 로거 설정.
    콘솔 + 파일(logs/app.log) 두 곳에 동시에 기록.
"""

import logging
import os
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"


def setup_logger() -> logging.Logger:
    """로거를 설정하고 반환. 이미 핸들러가 있으면 재설정하지 않음."""
    logger = logging.getLogger("hr_assistant")

    # 이미 설정된 경우 재설정 방지 (서버 재시작 시 핸들러 중복 방지)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # logs/ 폴더 없으면 생성
    LOG_DIR.mkdir(exist_ok=True)

    # 로그 형식: 시간 | 레벨 | 메시지
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 출력
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 파일 출력 (logs/app.log에 누적 저장)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 모듈 임포트 시 바로 사용할 수 있도록 전역 로거 생성
logger = setup_logger()
