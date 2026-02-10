"""
General Agent Graph
장소 검색/추천용 경량 파이프라인입니다.

그래프 구조:
    START
      ↓
    query_analyzer (질문 분석 + 검색 쿼리 생성)
      ↓
    search_node (Vector + Keyword 통합 검색)
      ↓
    enrichment_node (장소 상세 정보 조회)
      ↓
    response_node (LLM으로 장소 리스트 포맷팅)
      ↓
    END
"""

from langgraph.graph import StateGraph, END

from .state import GeneralAgentState
from .nodes import (
    query_analyzer,
    search_node,
    enrichment_node,
    response_node,
)


def create_general_agent_graph() -> StateGraph:
    """경량 장소 검색/추천 에이전트 그래프를 생성합니다."""
    graph_builder = StateGraph(GeneralAgentState)

    # 노드 추가
    graph_builder.add_node("query_analyzer", query_analyzer)
    graph_builder.add_node("search_node", search_node)
    graph_builder.add_node("enrichment_node", enrichment_node)
    graph_builder.add_node("response_node", response_node)

    # 순차 파이프라인
    graph_builder.set_entry_point("query_analyzer")
    graph_builder.add_edge("query_analyzer", "search_node")
    graph_builder.add_edge("search_node", "enrichment_node")
    graph_builder.add_edge("enrichment_node", "response_node")
    graph_builder.add_edge("response_node", END)

    graph = graph_builder.compile()
    return graph


# 외부에서 import 할 수 있도록 그래프 인스턴스 생성
app = create_general_agent_graph()
