"""
Google Place Search Node (Async Version - Native)
Google Places API를 호출하여 여러 가게 정보와 리뷰를 완전한 비동기로 수집합니다.
"""

import os
import re
import asyncio
import aiohttp
from typing import Any, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from ..config import config
from ..state import AgentState

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")


async def _search_places_async(session: aiohttp.ClientSession, query: str, max_results: int = 5) -> List[dict]:
    """Google Places API로 여러 장소를 비동기 검색합니다."""
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.name,places.displayName,places.formattedAddress,places.location,places.priceLevel"
    }
    
    payload = {
        "textQuery": query,
        "languageCode": "ko",
        "maxResultCount": min(max_results, 20)
    }
    
    try:
        async with session.post(url, headers=headers, json=payload, timeout=10) as response:
            result = await response.json()
            if "places" in result:
                return result["places"][:max_results]
    except Exception as e:
        print(f"⚠️ Place 검색 오류: {e}")
    
    return []


async def _get_place_reviews_async(session: aiohttp.ClientSession, place_name_id: str, place_name: str) -> dict:
    """장소의 상세 정보와 리뷰를 비동기로 가져옵니다."""
    url = f"https://places.googleapis.com/v1/{place_name_id}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "rating,userRatingCount,reviews.originalText,reviews.text,reviews.rating,reviews.relativePublishTimeDescription,photos.name,priceLevel"
    }
    
    params = {"languageCode": "ko"}
    
    try:
        async with session.get(url, headers=headers, params=params, timeout=10) as response:
            details = await response.json()
            
            return {
                "place_name": place_name,
                "rating": details.get('rating', 0),
                "total_reviews": details.get('userRatingCount', 0),
                "reviews": details.get('reviews', []),
                "photo_name": details.get('photos', [{}])[0].get('name') if details.get('photos') else None,
                "price_level": details.get('priceLevel', "")
            }
    except Exception as e:
        print(f"⚠️ {place_name} 리뷰 조회 오류: {e}")
        return {
            "place_name": place_name,
            "rating": 0,
            "total_reviews": 0,
            "reviews": []
        }


async def _normalize_names_to_korean_async(place_data_list: list[dict]) -> list[dict]:
    """
    (비동기 함수) 가게 이름들이 영어/일어인 경우 Gemini를 사용하여 한글로 변환합니다.
    """
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0,
    )
    
    targets = []
    for item in place_data_list:
        name = item["name"]
        if not re.search(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', name):
            targets.append(name)
    
    if not targets:
        return place_data_list
    
    prompt = f"""다음 외국어(영어/일어 등)로 된 식당 이름들을 한국인들이 네이버 검색 시 가장 많이 사용하는 한글 표기법으로 변환해줘.
원래 고유 명사 느낌을 최대한 살려줘.

입력 리스트: {targets}

출력 형식: JSON 배열 [ "한글이름1", "한글이름2", ... ] (순서 엄수, 다른 설명 없이 배열만 출력)"""
    
    try:
        # Async invoke
        response = await llm.ainvoke(prompt)
        match = re.search(r'\[.*\]', response.content, re.DOTALL)
        if match:
            korean_names = eval(match.group(0))
            k_idx = 0
            for item in place_data_list:
                if not re.search(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', item["name"]) and k_idx < len(korean_names):
                    old_name = item["name"]
                    item["name"] = korean_names[k_idx]
                    print(f"  🔤 이름 변환: {old_name} ➡️ {item['name']}")
                    k_idx += 1
    except Exception as e:
        print(f"  ⚠️ 이름 한글화 실패: {e}")
        
    return place_data_list


async def _run_google_search_logic(queries: List[str], result_count: int) -> List[dict]:
    """검색 및 리뷰 수집 전체 로직을 비동기로 실행"""
    async with aiohttp.ClientSession() as session:
        # 1. 병렬 검색
        search_tasks = [
            _search_places_async(session, q, result_count)
            for q in queries
        ]
        search_results_list = await asyncio.gather(*search_tasks)
        
        # 결과 합치기 및 중복 제거
        all_places = []
        seen_names = set()
        for results in search_results_list:
            if results:
                for p in results:
                    name = p['displayName']['text']
                    if name not in seen_names:
                        all_places.append(p)
                        seen_names.add(name)
        
        if not all_places:
            return []
            
        print(f"📍 {len(all_places)}개 가게 발견, 리뷰 수집 중...")
        
        # 2. 병렬 리뷰 수집
        detail_tasks = [
            _get_place_reviews_async(session, place['name'], place['displayName']['text'])
            for place in all_places
        ]
        
        details_list = await asyncio.gather(*detail_tasks)
        
        # 데이터 병합
        place_data_list = []
        for place, details in zip(all_places, details_list):
            place_data_list.append({
                "id": place['name'],
                "name": place['displayName']['text'],
                "address": place['formattedAddress'],
                "lat": place.get('location', {}).get('latitude', 0.0),
                "lng": place.get('location', {}).get('longitude', 0.0),
                "rating": details['rating'],
                "total_reviews": details['total_reviews'],
                "photo_name": details.get('photo_name'),
                "price_level": details.get('price_level', ""),
                "reviews": [
                    {
                        "rating": r.get('rating', 0),
                        "text": r.get('text', {}).get('text') or r.get('originalText', {}).get('text') or "",
                        "time": r.get('relativePublishTimeDescription', '')
                    }
                    for r in details['reviews'][:3]
                ]
            })
            print(f"  ✅ {place['displayName']['text']} (⭐{details['rating']})")
            
        return place_data_list


async def google_place_search_node(state: AgentState) -> dict[str, Any]:
    """
    Google Place API를 호출하여 여러 맛집 정보를 비동기로 조회하는 노드입니다. (Native Async)
    """
    if not GOOGLE_MAPS_API_KEY:
        print("⚠️ GOOGLE_CLOUD_API_KEY가 설정되지 않았습니다.")
        return {"place_data": None}
    
    query_plan = state.get("query_plan")
    queries = query_plan.get("place_queries", [])
    
    if not queries:
        if query_plan.get("place_query"):
            queries = [query_plan["place_query"]]
        else:
            print("ℹ️ Place 검색 쿼리 없음 - Google Place Search 스킵")
            return {"place_data": None}
    
    result_count = min(query_plan.get("result_count", 3), 5)
    
    print(f"🔍 Google Place 검색 쿼리 목록: {queries} (쿼리당 최대 {result_count}개)")
    
    try:
        # Native Await
        place_data_list = await _run_google_search_logic(queries, result_count)
    except Exception as e:
        print(f"❌ 검색 프로세스 오류: {e}")
        return {"place_data": None}
    
    if not place_data_list:
        print(f"❌ 검색 결과 없음")
        return {"place_data": None}
    
    # 외국어 이름을 한글로 변환 (비동기 처리)
    place_data_list = await _normalize_names_to_korean_async(place_data_list)
    
    print(f"✅ Google Place 검색 완료: 총 {len(place_data_list)}개 가게")
    
    return {"place_data": place_data_list}
