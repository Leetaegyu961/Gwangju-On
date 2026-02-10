"""
Search Node (General Agent)
Vector DB + Google Places Keyword 검색을 통합하여 수행합니다.
메인 에이전트의 vector_db 도구와 keyword_search 로직을 재사용합니다.
"""

import os
import asyncio
import aiohttp
from typing import Any, List
from dotenv import load_dotenv

from src.agent.tools.vector_db import vector_db
from ..state import GeneralAgentState

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")


async def _keyword_search(session: aiohttp.ClientSession, query: str, max_results: int = 10) -> List[dict]:
    """Google Places Text Search로 키워드 기반 장소 검색"""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
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
        print(f"[General-Search] Keyword search error for '{query}': {e}")

    return []


async def search_node(state: GeneralAgentState) -> dict[str, Any]:
    """
    Vector DB + Keyword 검색을 병렬 실행하여 장소 후보를 수집합니다.
    """
    query_plan = state.get("query_plan") or {}
    queries = query_plan.get("place_queries", [])
    result_count = query_plan.get("result_count", 10)

    if not queries:
        print("[General-Search] 검색 쿼리 없음. 스킵.")
        return {"search_results": []}

    print(f"[General-Search] 검색 시작: 쿼리 {len(queries)}개")

    # 1. Keyword Search (Google Places)
    keyword_results = []
    if GOOGLE_MAPS_API_KEY:
        async with aiohttp.ClientSession() as session:
            tasks = [_keyword_search(session, q, result_count) for q in queries]
            results = await asyncio.gather(*tasks)
            for places in results:
                keyword_results.extend(places)

    # 2. Vector Search (async)
    vector_results = []
    try:
        unique_queries = list(set(queries))
        for q in unique_queries:
            items = await vector_db.search(q, k=result_count)
            vector_results.extend(items)
    except Exception as e:
        print(f"[General-Search] Vector search error: {e}")

    # 3. 중복 제거 (이름 기반)
    seen_names = set()
    merged = []

    for kc in keyword_results:
        name = kc.get("displayName", {}).get("text", "")
        if name and name not in seen_names:
            seen_names.add(name)
            merged.append({
                "google_id": kc.get("name"),  # places/PLACE_ID
                "name": name,
                "source": "keyword",
                "raw": kc
            })

    for vc in vector_results:
        name = vc.get("place_name") or vc.get("id", "")
        if name and name not in seen_names:
            seen_names.add(name)
            merged.append({
                "google_id": vc.get("data", {}).get("google_place_id"),
                "name": name,
                "source": "vector",
                "keywords": vc.get("keywords", {})
            })

    print(f"[General-Search] 총 {len(merged)}개 고유 장소 발견")
    return {"search_results": merged[:30]}  # 최대 30개
