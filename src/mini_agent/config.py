"""
Mini Agent Configuration
환경 변수 및 설정을 관리하는 모듈입니다.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Mini Agent 설정 클래스"""
    
    # Google Gemini API 설정
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    
    # Google Places API 설정
    GOOGLE_CLOUD_API_KEY: str = os.getenv("GOOGLE_CLOUD_API_KEY", "")
    
    # Naver API 설정
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")
    
    @classmethod
    def validate(cls) -> bool:
        """필수 설정이 있는지 확인합니다."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        if not cls.GOOGLE_CLOUD_API_KEY:
            raise ValueError("GOOGLE_CLOUD_API_KEY 환경 변수가 설정되지 않았습니다.")
        return True


config = Config()
