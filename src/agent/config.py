"""
Configuration Module
환경 변수 및 설정을 관리하는 모듈입니다.
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """에이전트 설정 클래스"""

    # Google Gemini API 설정
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # 에이전트 설정
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
    VERBOSE: bool = os.getenv("VERBOSE", "true").lower() == "true"

    @classmethod
    def validate(cls) -> bool:
        """필수 설정이 있는지 확인합니다."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return True


# 설정 인스턴스
config = Config()
