"""
Search Tool
웹 검색 도구입니다.
"""

from langchain_core.tools import tool


@tool
def search_tool(query: str) -> str:
    """
    주어진 쿼리로 웹 검색을 수행합니다.

    Args:
        query: 검색할 쿼리 문자열

    Returns:
        검색 결과 문자열
    """
    # TODO: 실제 검색 API 연동 (Tavily, DuckDuckGo 등)
    # 현재는 플레이스홀더 구현
    return f"'{query}'에 대한 검색 결과: 검색 API를 연동해주세요."
