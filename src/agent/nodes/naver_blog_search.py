"""
Naver Blog Search Node (Simplified)
Google Places 결과의 각 가게명으로 네이버 블로그를 검색하고 RSS 매칭된 항목만 수집합니다.
현재는 검색 로직이 바이패스되어 빈 리스트를 반환하도록 설정되어 있습니다.
"""

from typing import Any
from ..state import AgentState

async def naver_blog_search_node(state: AgentState) -> dict[str, Any]:
    """
    네이버 블로그 검색 및 RSS 매칭을 수행하는 노드입니다.
    현재는 Latency 최적화를 위해 실제 검색을 수행하지 않고 빈 결과를 반환합니다.
    """
    place_data_list = state.get("place_data")
    if not place_data_list:
        return {"enriched_results": None}

    print(f"\n🔗 Naver 블로그 검색 SKIPPED (Latency Optimization): {len(place_data_list)}개 가게")
    
    # Bypass Naver Search -> Return empty blogs
    enriched_results = []
    for place in place_data_list:
        enriched_results.append({
            "place": place,
            "blogs": []
        })

    return {"enriched_results": enriched_results}
