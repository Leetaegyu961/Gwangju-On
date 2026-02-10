"""
General Agent State
경량 에이전트의 상태를 정의하는 모듈입니다.
서베이 데이터, 개인화 스코어링 등 불필요한 필드를 제거한 간소화 버전입니다.
"""

from typing import Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GeneralAgentState(TypedDict):
    """일반 검색/추천 에이전트의 상태"""

    # 메시지 히스토리
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 검색 쿼리 계획
    query_plan: dict | None

    # 검색 결과 (vector + keyword 통합)
    search_results: list | None

    # 상세 정보가 추가된 결과
    enriched_results: list | None

    # 최종 응답 (JSON 문자열)
    final_answer: str | None
