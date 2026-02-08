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
        tool_results: 도구 실행 결과
        query_plan: LLM이 생성한 검색 쿼리
        naver_search_data: 네이버 블로그 검색 결과
        enriched_results: 블로그 + Places 리뷰가 매칭된 통합 데이터
        final_answer: 최종 응답
    """

    # 메시지 히스토리 - add_messages reducer로 자동 누적
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 현재 단계 (예: "thinking", "tool_calling", "responding")
    current_step: str

    # 도구 실행 결과 저장
    tool_results: dict | None

    # 쿼리 계획 (LLM이 생성한 검색 쿼리)
    query_plan: dict | None

    # [New] Vector DB 검색 결과 (Parallel Hybrid RAG)
    vector_candidates: list | None
    
    # [New] Keyword 검색 결과 (Parallel Hybrid RAG - Lightweight)
    keyword_candidates: list | None
    
    # [Deprecated] 이전 버전 호환성 유지 (필요 시 삭제)
    vector_search_results: list | None

    # Place API 결과 저장 (가게 목록 + 리뷰)
    place_data: list | None

    # 블로그 + Places 리뷰 통합 데이터
    enriched_results: list | None

    # 스코어링된 결과 (점수 포함)
    scored_results: list | None

    # 최종 응답
    final_answer: str | None

    # 사용자 서베이 데이터 (성별, 연령, 테마, 코스 구성 등)
    survey_data: dict | None

    # [New] QueryPlanner가 생성한 3가지 테마
    themes: list[str] | None

    # [New] 병렬 실행된 LLM 노드들의 결과 수집 (Reducer: 리스트 합치기)
    generated_courses: Annotated[list, operator.add]

    # [New] 사용자 ID (개인화 스코어링용)
    userId: str | None

    # [New] Naver Blog Search 실행 여부
    run_blog_search: bool | None
    
    # [New] Parallel Retrieval Candidates
    vector_candidates: list | None
    keyword_candidates: list | None



