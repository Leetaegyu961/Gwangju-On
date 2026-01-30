"""
Agent Graph (Parallel Execution Version)
LangGraph를 사용하여 에이전트 그래프를 정의하는 모듈입니다.
3개의 코스를 병렬로 생성하는 구조로 변경되었습니다.
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    google_place_search_node, 
    naver_blog_search_node, 
    query_planner_node, 
    scoring_node,
    generate_course_1,
    generate_course_2,
    generate_course_3,
    aggregator_node
)


def create_agent_graph() -> StateGraph:
    """
    에이전트 그래프를 생성합니다.

    그래프 구조:
        START 
          ↓
        query_planner_node (테마 3개 선정 + 쿼리 생성)
          ↓
        google_place_search_node (장소 검색)
          ↓
        naver_blog_search_node (블로그 리뷰 검색)
          ↓
        scoring_node (점수 계산 및 정렬)
          ↓ 
        [Parallel Execution] 
        ├── generate_course_1 (테마 1 코스 생성)
        ├── generate_course_2 (테마 2 코스 생성)
        └── generate_course_3 (테마 3 코스 생성)
          ↓
        aggregator_node (결과 취합 및 포맷팅)
          ↓
         END
    """
    # 그래프 빌더 생성
    graph_builder = StateGraph(AgentState)

    # 노드 추가
    graph_builder.add_node("query_planner_node", query_planner_node)
    graph_builder.add_node("google_place_search_node", google_place_search_node)
    graph_builder.add_node("naver_blog_search_node", naver_blog_search_node)
    graph_builder.add_node("scoring_node", scoring_node)
    
    # 병렬 코스 생성 노드
    graph_builder.add_node("generate_course_1", generate_course_1)
    graph_builder.add_node("generate_course_2", generate_course_2)
    graph_builder.add_node("generate_course_3", generate_course_3)
    
    # 취합 노드
    graph_builder.add_node("aggregator_node", aggregator_node)

    # 시작점
    graph_builder.set_entry_point("query_planner_node")

    # 검색 및 스코어링 단계 (순차)
    graph_builder.add_edge("query_planner_node", "google_place_search_node")
    graph_builder.add_edge("google_place_search_node", "naver_blog_search_node")
    graph_builder.add_edge("naver_blog_search_node", "scoring_node")
    
    # 병렬 실행 (Fan-out)
    graph_builder.add_edge("scoring_node", "generate_course_1")
    graph_builder.add_edge("scoring_node", "generate_course_2")
    graph_builder.add_edge("scoring_node", "generate_course_3")
    
    # 결과 취합 (Fan-in)
    graph_builder.add_edge("generate_course_1", "aggregator_node")
    graph_builder.add_edge("generate_course_2", "aggregator_node")
    graph_builder.add_edge("generate_course_3", "aggregator_node")
    
    # 종료
    graph_builder.add_edge("aggregator_node", END)

    # 그래프 컴파일
    graph = graph_builder.compile()

    return graph


# 외부에서 import 할 수 있도록 그래프 인스턴스 생성
app = create_agent_graph()
