"""
Keyword Retrieval Node
Google Places Text Search를 사용하여 키워드 기반으로 장소들을 검색하는 노드입니다.
(Parallel Hybrid RAG: Fan-Out Phase 2 - Keyword Search)
"""

import os
import asyncio
import aiohttp
from typing import Any, List
from dotenv import load_dotenv
from ..state import AgentState

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")

async def _search_places_async(session: aiohttp.ClientSession, query: str, max_results: int = 5) -> List[dict]:
    """Google Places API로 여러 장소를 비동기 검색합니다 (Lightweight)."""
    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        # Minimal fields for retrieval
        "X-Goog-FieldMask": (
            "places.name,places.displayName,places.formattedAddress,"
            "places.location,places.priceLevel,places.types"
        )
    }

    payload = {
        "textQuery": query,
        "languageCode": "ko",
        "regionCode": "KR",
        "pageSize": min(max_results, 20),
    }

    try:
        async with session.post(url, headers=headers, json=payload, timeout=10) as response:
            result = await response.json()
            if "places" in result:
                return result["places"][:max_results]
    except Exception as e:
        print(f"[KeywordRetrieval] Error searching for '{query}': {e}")

    return []

async def keyword_retrieval_node(state: AgentState) -> dict[str, Any]:
    """
    Google Places Text Search를 수행하여 키워드 매칭 장소들을 찾습니다.
    (Pure Retrieval: 상세 정보/리뷰 없이 후보군만 확보)
    
    Args:
        state: AgentState
        
    Returns:
        dict: {"keyword_candidates": [...]}
    """
    if not GOOGLE_MAPS_API_KEY:
        print("[KeywordRetrieval] ⚠️ API Key missing. Skipping.")
        return {"keyword_candidates": []}

    query_plan = state.get("query_plan") or {}
    queries = query_plan.get("place_queries", [])

    if not queries:
        if query_plan.get("place_query"):
            queries = [query_plan["place_query"]]
        else:
            print("[KeywordRetrieval] ⚠️ No queries found. Skipping.")
            return {"keyword_candidates": []}

    result_count = min(query_plan.get("result_count", 5), 10)
    print(f"[KeywordRetrieval] 🔍 검색 시작: 쿼리 {len(queries)}개")

    # Deduplicate queries
    unique_queries = list(set(queries))

    async with aiohttp.ClientSession() as session:
        search_tasks = [
            _search_places_async(session, q, result_count)
            for q in unique_queries
        ]
        
        results_list = await asyncio.gather(*search_tasks)

    # Flatten Results
    all_candidates = []
    seen_ids = set()

    for results in results_list:
        for place in results:
            pid = place.get("name") # places/PLACE_ID
            if pid and pid not in seen_ids:
                all_candidates.append(place)
                seen_ids.add(pid)

    print(f"[KeywordRetrieval] ✅ 총 {len(all_candidates)}개 고유 장소 발견")

    return {"keyword_candidates": all_candidates}
