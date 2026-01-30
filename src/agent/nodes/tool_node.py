"""
Tool Node
도구 실행을 담당하는 노드입니다.
"""

from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode as LangGraphToolNode

from ..state import AgentState
from ..tools import search_tool


# 사용 가능한 도구 목록
TOOLS = [search_tool]

# LangGraph 내장 ToolNode 활용
tool_executor = LangGraphToolNode(TOOLS)


async def tool_node(state: AgentState) -> dict[str, Any]:
    """
    도구를 실행하고 결과를 반환하는 노드입니다.

    Args:
        state: 현재 에이전트 상태

    Returns:
        업데이트된 상태 (messages, tool_results, current_step)
    """
    # LangGraph ToolNode를 사용하여 도구 실행
    result = await tool_executor.ainvoke(state)

    return {
        "messages": result["messages"],
        "current_step": "thinking",
    }
