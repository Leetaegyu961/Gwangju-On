"""
Agent Graph
LangGraph를 사용하여 에이전트 그래프를 정의하는 모듈입니다.
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import llm_node, tool_node


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

    그래프 구조:
        START -> llm_node -> (조건) -> tool_node -> llm_node (반복)
                                   -> END

    Returns:
        컴파일된 StateGraph
    """
    # 그래프 빌더 생성
    graph_builder = StateGraph(AgentState)

    # 노드 추가
    graph_builder.add_node("llm_node", llm_node)
    graph_builder.add_node("tool_node", tool_node)

    # 시작점 설정
    graph_builder.set_entry_point("llm_node")

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
