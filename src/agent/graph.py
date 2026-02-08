"""
Agent Graph (Parallel Hybrid RAG Version)
LangGraph를 사용하여 에이전트 그래프를 정의하는 모듈입니다.
Parallel Hybrid RAG (Vector + Keyword) 및 병렬 코스 생성을 포함합니다.
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    vector_retrieval_node,
    keyword_retrieval_node,
    enrichment_node,
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
          ↓ (Fan-Out: Parallel Retrieval)
        ├─ vector_retrieval_node (Vector Search)
        └─ keyword_retrieval_node (Keyword Search)
          ↓ (Fan-In: Merge & Enrich)
        enrichment_node (통합 및 상세 정보 조회)
          ↓
        naver_blog_search_node (블로그 리뷰 검색)
          ↓
        scoring_node (점수 계산 및 정렬)
          ↓ (Fan-Out: Parallel Generation)
        ├── generate_course_1 (테마 1 코스 생성)
        ├── generate_course_2 (테마 2 코스 생성)
        └── generate_course_3 (테마 3 코스 생성)
          ↓ (Fan-In: Aggregate)
        aggregator_node (결과 취합 및 포맷팅)
          ↓
         END
    """
    # 그래프 빌더 생성
    graph_builder = StateGraph(AgentState)

    # 노드 추가
    graph_builder.add_node("query_planner_node", query_planner_node)
    
    # Parallel Retrieval Nodes
    graph_builder.add_node("vector_retrieval_node", vector_retrieval_node)
    graph_builder.add_node("keyword_retrieval_node", keyword_retrieval_node)
    
    # Enrichment Node
    graph_builder.add_node("enrichment_node", enrichment_node)
    
    # Existing Nodes
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

    # [Retrieval Phase] Fan-Out
    graph_builder.add_edge("query_planner_node", "vector_retrieval_node")
    graph_builder.add_edge("query_planner_node", "keyword_retrieval_node")
    
    # [Retrieval Phase] Fan-In
    graph_builder.add_edge("vector_retrieval_node", "enrichment_node")
    graph_builder.add_edge("keyword_retrieval_node", "enrichment_node")
    
    # [Processing Phase]
    # Conditional Edge for Naver Blog Search
    def route_blog_search(state: AgentState) -> Literal["naver_blog_search_node", "scoring_node"]:
        # 기본적으로 run_blog_search 플래그가 True일 때만 실행
        if state.get("run_blog_search"):
            return "naver_blog_search_node"
        return "scoring_node"

    graph_builder.add_conditional_edges(
        "enrichment_node",
        route_blog_search,
        {
            "naver_blog_search_node": "naver_blog_search_node",
            "scoring_node": "scoring_node"
        }
    )
    graph_builder.add_edge("naver_blog_search_node", "scoring_node")
    
    # [Generation Phase] Fan-Out
    graph_builder.add_edge("scoring_node", "generate_course_1")
    graph_builder.add_edge("scoring_node", "generate_course_2")
    graph_builder.add_edge("scoring_node", "generate_course_3")
    
    # [Generation Phase] Fan-In
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
