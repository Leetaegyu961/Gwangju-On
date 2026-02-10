"""
Enrichment Node (General Agent)
검색 결과에 상세 정보(리뷰, 평점, 사진 등)를 추가합니다.
메인 에이전트의 enrichment 헬퍼 함수를 재사용합니다.
"""

from typing import Any

from src.agent.nodes.enrichment_node import (
    _fetch_place_with_resolution,
    _normalize_names_to_korean_async,
    _normalize_formatted_address,
)
from ..state import GeneralAgentState

import asyncio
import aiohttp


async def enrichment_node(state: GeneralAgentState) -> dict[str, Any]:
    """
    search_results의 각 장소에 대해 Google Places 상세 정보를 조회합니다.
    """
    search_results = state.get("search_results", [])

    if not search_results:
        print("[General-Enrich] 검색 결과 없음. 스킵.")
        return {"enriched_results": []}

    print(f"[General-Enrich] {len(search_results)}개 장소 상세 조회 중...")

    enriched = []

    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_place_with_resolution(session, c) for c in search_results]
        results = await asyncio.gather(*tasks)

        for candidate, details in results:
            if not details:
                continue

            formatted = details.get('formattedAddress', '')
            components = details.get('addressComponents', None)
            normalized_address = _normalize_formatted_address(formatted, components)

            place_obj = {
                "id": details['name'],
                "name": details.get('displayName', {}).get('text', candidate['name']),
                "address": normalized_address,
                "lat": details.get('location', {}).get('latitude', 0.0),
                "lng": details.get('location', {}).get('longitude', 0.0),
                "rating": details.get('rating', 0),
                "total_reviews": details.get('userRatingCount', 0),
                "photo_name": details.get('photos', [{}])[0].get('name') if details.get('photos') else None,
                "price_level": details.get('priceLevel', ""),
                "reviews": [
                    {
                        "rating": r.get('rating', 0),
                        "text": r.get('text', {}).get('text') or r.get('originalText', {}).get('text') or "",
                        "time": r.get('relativePublishTimeDescription', '')
                    }
                    for r in details.get('reviews', [])[:3]
                ],
                "source": candidate.get("source", ""),
                "keywords": candidate.get("keywords", {})
            }
            enriched.append({"place": place_obj})

    # 외국어 이름 한글 변환
    place_list = [e["place"] for e in enriched]
    place_list = await _normalize_names_to_korean_async(place_list)
    for i, place in enumerate(place_list):
        enriched[i]["place"] = place

    print(f"[General-Enrich] 완료: {len(enriched)}개 장소")
    return {"enriched_results": enriched}
