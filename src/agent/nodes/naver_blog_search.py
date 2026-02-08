"""
Naver Blog Search Node (Simplified)
Google Places 결과의 각 가게명으로 네이버 블로그를 검색하고 RSS 매칭된 항목만 수집합니다.
현재는 검색 로직이 바이패스되어 빈 리스트를 반환하도록 설정되어 있습니다.
"""

from typing import Any
from ..state import AgentState

async def naver_blog_search_node(state: AgentState) -> dict[str, Any]:
    """
    네이버 블로그 검색 노드 (Conditional)
    state['enriched_results']를 입력받아 블로그 정보를 추가(Update)합니다.
    """
    enriched_results = state.get("enriched_results")
    if not enriched_results:
        return {"enriched_results": []}

    print(f"\n🟢 [Naver Blog Search] 블로그 검색 실행 (Conditional): {len(enriched_results)}개 가게")
    
    # TODO: Implement actual Naver API call here if needed in the future.
    # Currently, we just keep the empty blogs list or add a placeholder.
    # Since Vector DB provides semantic context, this is a fallback.
    
    # Example logic:
    # for item in enriched_results:
    #     query = item['place']['name']
    #     blogs = await search_naver_blog(query)
    #     item['blogs'] = blogs
    
    # For now, just pass through (but print ensures we know it ran)
    
    return {"enriched_results": enriched_results}
