"""
Agent Graph (네이버 → Place Enrichment 순차 실행)
LangGraph를 사용하여 에이전트 그래프를 정의하는 모듈입니다.
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import llm_node, tool_node, google_place_search_node, naver_blog_search_node, query_planner_node, scoring_node


def should_continue(state: AgentState) -> Literal["tool_node", "end"]:
    """
    다음 노드를 결정하는 조건부 엣지 함수입니다.

    Args:
        state: 현재 에이전트 상태

    Returns:
        다음 노드 이름 ("tool_node" 또는 "end")
    """
    current_step = state.get("current_step", "")

    if current_step == "tool_calling":
        return "tool_node"
    else:
        return "end"


def create_agent_graph() -> StateGraph:
    """
    에이전트 그래프를 생성합니다.

    그래프 구조 (스코어링 적용):
        START 
          ↓
        query_planner_node (LLM이 쿼리 생성)
          ↓
        google_place_search_node (Google Places로 5개 가게 + 리뷰 검색)
          ↓
        naver_blog_search_node (각 가게명으로 블로그 검색, RSS 매칭)
          ↓
        scoring_node (공공 데이터 + API 데이터 기반 점수 계산)
          ↓
        llm_node → (조건) → tool_node → llm_node (반복)
                          → END

    Returns:
        컴파일된 StateGraph
    """
    # 그래프 빌더 생성
    graph_builder = StateGraph(AgentState)

    # 노드 추가
    graph_builder.add_node("query_planner_node", query_planner_node)
    graph_builder.add_node("google_place_search_node", google_place_search_node)
    graph_builder.add_node("naver_blog_search_node", naver_blog_search_node)
    graph_builder.add_node("scoring_node", scoring_node)  # 스코어링 노드 추가
    graph_builder.add_node("llm_node", llm_node)
    graph_builder.add_node("tool_node", tool_node)

    # 시작점: Query Planner부터 시작
    graph_builder.set_entry_point("query_planner_node")

    # 순차 실행: query_planner → google_place_search → naver_blog_search → scoring → llm
    graph_builder.add_edge("query_planner_node", "google_place_search_node")
    graph_builder.add_edge("google_place_search_node", "naver_blog_search_node")
    graph_builder.add_edge("naver_blog_search_node", "scoring_node")  # 스코어링 추가
    graph_builder.add_edge("scoring_node", "llm_node")  # 스코어링 후 LLM으로

    # 조건부 엣지 추가 (LLM 노드 이후)
    graph_builder.add_conditional_edges(
        "llm_node",
        should_continue,
        {
            "tool_node": "tool_node",
            "end": END,
        },
    )

    # tool_node -> llm_node (도구 실행 후 다시 LLM으로)
    graph_builder.add_edge("tool_node", "llm_node")

    # 그래프 컴파일
    graph = graph_builder.compile()

    return graph


# 외부에서 import 할 수 있도록 그래프 인스턴스 생성
app = create_agent_graph()
