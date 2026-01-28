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
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    # LangSmith 트레이싱 설정
    LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "false")
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "default")

    # 에이전트 설정
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
    VERBOSE: bool = os.getenv("VERBOSE", "true").lower() == "true"

    @classmethod
    def validate(cls) -> bool:
        """필수 설정이 있는지 확인합니다."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return True
    
    @classmethod
    def enable_langsmith(cls) -> None:
        """LangSmith 트레이싱을 활성화합니다."""
        if cls.LANGSMITH_TRACING.lower() == "true" and cls.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_ENDPOINT"] = cls.LANGSMITH_ENDPOINT
            os.environ["LANGCHAIN_API_KEY"] = cls.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = cls.LANGSMITH_PROJECT
            print(f"✅ LangSmith 트레이싱 활성화: {cls.LANGSMITH_PROJECT}")


# 설정 인스턴스
config = Config()

# LangSmith 자동 활성화
config.enable_langsmith()
