"""
Agent State Definition
에이전트의 상태를 정의하는 모듈입니다.
"""

import operator
from typing import Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    에이전트의 상태를 나타내는 TypedDict 클래스입니다.

    Attributes:
        messages: 대화 메시지 히스토리 (자동으로 누적됨)
        current_step: 현재 에이전트가 수행 중인 단계
        query_plan: LLM이 생성한 검색 쿼리
        enriched_results: 통합 데이터 (장소 상세 + 블로그)
        final_answer: 최종 응답
    """

    # 메시지 히스토리 - add_messages reducer로 자동 누적
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 현재 단계 (예: "thinking", "responding")
    current_step: str

    # 쿼리 계획 (LLM이 생성한 검색 쿼리)
    query_plan: dict | None

    # Vector DB 검색 결과 (Parallel Hybrid RAG)
    vector_candidates: list | None

    # Keyword 검색 결과 (Parallel Hybrid RAG - Lightweight)
    keyword_candidates: list | None

    # 블로그 + Places 리뷰 통합 데이터
    enriched_results: list | None

    # 스코어링된 결과 (점수 포함)
    scored_results: list | None

    # 최종 응답
    final_answer: str | None

    # 사용자 서베이 데이터 (성별, 연령, 테마, 코스 구성 등)
    survey_data: dict | None

    # QueryPlanner가 생성한 3가지 테마
    themes: list[str] | None

    # 병렬 실행된 LLM 노드들의 결과 수집 (Reducer: 리스트 합치기)
    generated_courses: Annotated[list, operator.add]

    # 사용자 ID (개인화 스코어링용)
    userId: str | None

    # Naver Blog Search 실행 여부
    run_blog_search: bool | None

    # 개인화 컨텍스트 요약 (LLM이 생성한 사용자 선호/이력 요약문)
    personalization_context: str | None
