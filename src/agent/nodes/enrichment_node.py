"""
Enrichment Node (Optimized)
Vector Search와 Keyword Search의 후보군을 통합하고, 상세 정보를 조회(Enrichment)하는 노드입니다.
(Parallel Hybrid RAG: Fan-In Phase - Merge & Enrich)

최적화: ID Resolution과 Details Fetching을 단일 병렬 작업으로 통합
"""

import os
import re
import json
import asyncio
import aiohttp
from typing import Any, List, Dict
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from ..config import config
from ..state import AgentState

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")

# --- Helpers (Refactored from google_place_search.py) ---

def _normalize_formatted_address(formatted: str, address_components: list | None) -> str:
    """주소 정규화 (대한민국 제거, 상세 주소 정리)"""
    if not formatted:
        return formatted

    s = formatted.strip()
    for prefix in ("대한민국 ", "Republic of Korea ", "South Korea ", "Korea, Republic of ", "Korea, "):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()

    if address_components and any(tok in formatted for tok in ("South Korea", "Republic of Korea")):
        priority = [
            "administrative_area_level_1", "administrative_area_level_2", "locality",
            "sublocality_level_1", "sublocality_level_2", "sublocality_level_3",
            "route", "street_number", "premise"
        ]
        type_to_long = {}
        for c in address_components:
            if not isinstance(c, dict): continue
            long_text = c.get("longText")
            types = c.get("types", [])
            if not long_text: continue
            for t in types:
                type_to_long.setdefault(t, long_text)

        parts = []
        seen = set()
        for t in priority:
            v = type_to_long.get(t)
            if v and v not in seen:
                parts.append(v)
                seen.add(v)
        if parts:
            return " ".join(parts)

    return s

async def _get_place_details_async(session: aiohttp.ClientSession, place_id: str) -> dict:
    """Google Places ID(places/...)를 사용하여 상세 정보(리뷰, 평점 등)를 조회합니다."""
    url = f"https://places.googleapis.com/v1/{place_id}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "id,name,displayName,formattedAddress,addressComponents,location,"
            "rating,userRatingCount,priceLevel,"
            "reviews.originalText,reviews.text,reviews.rating,reviews.relativePublishTimeDescription,"
            "photos.name"
        )
    }
    params = {"languageCode": "ko"}

    try:
        async with session.get(url, headers=headers, params=params, timeout=10) as response:
            if response.status != 200:
                print(f"[Enrichment] ⚠️ Failed to fetch details for {place_id}: {response.status}")
                return None
            return await response.json()
    except Exception as e:
        print(f"[Enrichment] ❌ Error details for {place_id}: {e}")
        return None

async def _resolve_place_id_async(session: aiohttp.ClientSession, query: str) -> str | None:
    """장소 이름으로 Text Search를 수행하여 Google Place ID를 찾습니다 (Vector DB 결과 보완용)."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.name"
    }
    payload = {"textQuery": query, "pageSize": 1}
    
    try:
        async with session.post(url, headers=headers, json=payload, timeout=5) as response:
            res = await response.json()
            if "places" in res and res["places"]:
                return res["places"][0]["name"] # places/PLACE_ID
    except Exception as e:
        print(f"[Enrichment] ⚠️ Resolution failed for '{query}': {e}")
    return None


async def _fetch_place_with_resolution(
    session: aiohttp.ClientSession, 
    candidate: dict
) -> tuple[dict, dict | None]:
    """
    [최적화] ID Resolution과 Details Fetching을 하나의 작업으로 통합.
    Google ID가 없으면 먼저 resolve하고, 그 다음 details를 가져옵니다.
    
    Returns:
        (candidate, details) 튜플. details가 None이면 실패.
    """
    google_id = candidate.get("google_id")
    
    # 1. ID가 없으면 먼저 resolve
    if not google_id:
        name = candidate.get("name", "")
        if name:
            google_id = await _resolve_place_id_async(session, name)
            candidate["google_id"] = google_id
    
    # 2. ID가 있으면 details fetch
    if google_id:
        details = await _get_place_details_async(session, google_id)
        return (candidate, details)
    
    return (candidate, None)


async def _normalize_names_to_korean_async(place_data_list: list[dict]) -> list[dict]:
    """Gemini를 사용하여 외국어 이름을 한글로 변환합니다."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0,
        )
        
        targets = []
        indices = []
        for idx, item in enumerate(place_data_list):
            name = item["name"]
            if not re.search(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', name):
                targets.append(name)
                indices.append(idx)
        
        if not targets:
            return place_data_list

        prompt = f"""다음 외국어(영어/일어 등)로 된 식당 이름들을 한국인들이 검색하는 한글 표기로 변환해줘.
입력: {targets}
출력 형식: JSON 배열 [ "한글이름1", "한글이름2", ... ] (설명 없이 JSON만)"""

        response = await llm.ainvoke(prompt)
        match = re.search(r'\[.*\]', response.content, re.DOTALL)
        if match:
            korean_names = json.loads(match.group(0))
            for i, k_name in zip(indices, korean_names):
                if i < len(place_data_list):
                    print(f"[Trans] {place_data_list[i]['name']} -> {k_name}")
                    place_data_list[i]['name'] = k_name
    except Exception as e:
        print(f"[Enrichment] ⚠️ Name normalization failed: {e}")
    
    return place_data_list

# --- Main Node ---

async def enrichment_node(state: AgentState) -> dict[str, Any]:
    """
    Vector Candidates + Keyword Candidates -> Deduplication -> Details Fetching
    [최적화] ID Resolution과 Details Fetching을 단일 병렬 작업으로 통합
    """
    vector_candidates = state.get("vector_candidates", [])
    keyword_candidates = state.get("keyword_candidates", [])
    
    # 1. Merge & Deduplicate
    candidates_map = {} # Key: ID or Name, Value: Candidate Object
    
    # Process Keyword Candidates (Already have Google IDs)
    for kc in keyword_candidates:
        pid = kc.get("name") # places/...
        if pid:
            candidates_map[pid] = {
                "google_id": pid,
                "name": kc.get("displayName", {}).get("text"),
                "source": "keyword",
                "raw": kc
            }
            
    # Process Vector Candidates
    for vc in vector_candidates:
        name = vc.get("place_name") or vc.get("id")
        g_id = vc.get("data", {}).get("google_place_id")
        
        if g_id:
             if g_id in candidates_map:
                 candidates_map[g_id]["source"] = "hybrid"
                 candidates_map[g_id]["vector_score"] = vc.get("similarity_score")
             else:
                 candidates_map[g_id] = {
                     "google_id": g_id,
                     "name": name,
                     "source": "vector",
                     "vector_score": vc.get("similarity_score"),
                     "keywords": vc.get("keywords", {})
                 }
        else:
            # No Google ID, needs resolution
            found = False
            for k, v in candidates_map.items():
                if v.get("name") == name:
                    v["source"] = "hybrid"
                    v["vector_score"] = vc.get("similarity_score")
                    if not v.get("keywords"):
                        v["keywords"] = vc.get("keywords", {})
                    found = True
                    break
            
            if not found:
                candidates_map[f"TEMP_{name}"] = {
                    "google_id": None,
                    "name": name,
                    "source": "vector",
                    "vector_score": vc.get("similarity_score"),
                    "keywords": vc.get("keywords", {})
                }

    print(f"[Enrichment] 🧩 Merged Candidates: {len(candidates_map)}")

    # 2. Limit Candidates (Cost Control)
    MAX_ENRICH = 30
    final_candidates = list(candidates_map.values())[:MAX_ENRICH]

    enriched_results = []
    
    async with aiohttp.ClientSession() as session:
        # [최적화] 단일 병렬 작업으로 ID Resolution + Details Fetching 통합
        print(f"[Enrichment] 📥 Fetching details for {len(final_candidates)} places (optimized)...")
        
        fetch_tasks = [
            _fetch_place_with_resolution(session, c) 
            for c in final_candidates
        ]
        
        results = await asyncio.gather(*fetch_tasks)
        
        # Process results
        for candidate, details in results:
            if not details: 
                continue
            
            formatted = details.get('formattedAddress', '')
            components = details.get('addressComponents', None)
            normalized_address = _normalize_formatted_address(formatted, components)
            
            place_obj = {
                "id": details['name'],
                "name": details.get('displayName', {}).get('text', candidate['name']),
                "original_name": details.get('displayName', {}).get('text', candidate['name']),
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
                "source": candidate["source"],
                "keywords": candidate.get("keywords", {})
            }
            enriched_results.append(place_obj)

    # Normalize Names (Optional, but good for UX)
    enriched_results = await _normalize_names_to_korean_async(enriched_results)
    
    # Wrap for ScoringNode compatibility
    final_results = []
    for place in enriched_results:
        final_results.append({
            "place": place,
            "blogs": []
        })
    
    print(f"[Enrichment] ✅ Completed: {len(enriched_results)} places ready.")
    return {"enriched_results": final_results}
