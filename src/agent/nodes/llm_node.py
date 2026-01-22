"""
LLM Node
LLM 호출을 담당하는 노드입니다.
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import config
from ..state import AgentState
from ..tools import search_tool


def llm_node(state: AgentState) -> dict[str, Any]:
    """
    LLM을 호출하여 응답을 생성하는 노드입니다.

    Args:
        state: 현재 에이전트 상태

    Returns:
        업데이트된 상태 (messages, current_step)
    """
    # LLM 초기화
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
    )

    # 도구 바인딩
    tools = [search_tool]
    llm_with_tools = llm.bind_tools(tools)

    # LLM 호출
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)

    # 도구 호출이 필요한지 확인
    if response.tool_calls:
        return {
            "messages": [response],
            "current_step": "tool_calling",
        }

    # 최종 응답
    return {
        "messages": [response],
        "current_step": "responding",
        "final_answer": response.content,
    }
