"""
Mini Agent - Google Place Search
Google Places API를 사용하여 장소 정보와 리뷰를 검색합니다.
"""

import asyncio
import aiohttp
from typing import List, Dict, Any

from .config import config


async def search_places(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Google Places API로 장소를 검색합니다.
    
    Args:
        query: 검색 쿼리 (예: "광주 동명동 맛집")
        max_results: 최대 결과 개수 (기본 10, 최대 20)
        
    Returns:
        장소 정보 리스트
    """
    if not config.GOOGLE_CLOUD_API_KEY:
        print("⚠️ GOOGLE_CLOUD_API_KEY가 설정되지 않았습니다.")
        return []
    
    async with aiohttp.ClientSession() as session:
        # 1. 장소 검색
        places = await _search_places_async(session, query, max_results)
        
        if not places:
            return []
        
        print(f"📍 {len(places)}개 장소 발견, 리뷰 수집 중...")
        
        # 2. 리뷰 병렬 수집
        detail_tasks = [
            _get_place_details_async(session, place['name'], place['displayName']['text'])
            for place in places
        ]
        details_list = await asyncio.gather(*detail_tasks)
        
        # 3. 데이터 병합
        result = []
        for place, details in zip(places, details_list):
            result.append({
                "id": place['name'],
                "name": place['displayName']['text'],
                "address": place.get('formattedAddress', ''),
                "lat": place.get('location', {}).get('latitude', 0.0),
                "lng": place.get('location', {}).get('longitude', 0.0),
                "rating": details.get('rating', 0),
                "total_reviews": details.get('total_reviews', 0),
                "photo_name": details.get('photo_name'),
                "reviews": details.get('reviews', [])[:3]  # 상위 3개 리뷰만
            })
            print(f"  ✅ {place['displayName']['text']} (⭐{details.get('rating', 0)})")
        
        print(f"✅ Place 검색 완료: {len(result)}개")
        return result


async def _search_places_async(
    session: aiohttp.ClientSession, 
    query: str, 
    max_results: int
) -> List[dict]:
    """Google Places Text Search API 호출"""
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": config.GOOGLE_CLOUD_API_KEY,
        "X-Goog-FieldMask": (
            "places.name,places.displayName,places.formattedAddress,"
            "places.location,places.priceLevel"
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
        print(f"⚠️ Place 검색 오류: {e}")
    
    return []


async def _get_place_details_async(
    session: aiohttp.ClientSession, 
    place_id: str, 
    place_name: str
) -> Dict[str, Any]:
    """장소 상세 정보 및 리뷰 조회"""
    url = f"https://places.googleapis.com/v1/{place_id}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": config.GOOGLE_CLOUD_API_KEY,
        "X-Goog-FieldMask": (
            "rating,userRatingCount,reviews.text,reviews.rating,"
            "reviews.relativePublishTimeDescription,photos.name"
        )
    }
    
    try:
        async with session.get(url, headers=headers, params={"languageCode": "ko"}, timeout=10) as response:
            details = await response.json()
            
            reviews = []
            for r in details.get('reviews', [])[:3]:
                reviews.append({
                    "rating": r.get('rating', 0),
                    "text": r.get('text', {}).get('text', ''),
                    "time": r.get('relativePublishTimeDescription', '')
                })
            
            return {
                "rating": details.get('rating', 0),
                "total_reviews": details.get('userRatingCount', 0),
                "reviews": reviews,
                "photo_name": details.get('photos', [{}])[0].get('name') if details.get('photos') else None
            }
    except Exception as e:
        print(f"⚠️ {place_name} 상세 정보 조회 오류: {e}")
        return {"rating": 0, "total_reviews": 0, "reviews": []}
