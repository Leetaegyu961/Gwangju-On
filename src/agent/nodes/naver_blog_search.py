"""
Naver Blog Search Node
Google Places 결과의 각 가게명으로 네이버 블로그를 검색하고 RSS 매칭된 항목만 수집합니다.
"""

import os
import urllib.request
import urllib.parse
import json
import re
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import feedparser

from ..state import AgentState

load_dotenv()
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


def _get_log_no(url: str) -> str | None:
    """URL에서 글 번호(logNo)만 추출합니다."""
    match = re.search(r'/(\d{10,})', url)
    if match:
        return match.group(1)
    return None


def _extract_blog_id(url: str) -> str | None:
    """블로그 ID 추출"""
    match = re.search(r'blog\.naver\.com/([^/]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'm\.blog\.naver\.com/([^/]+)', url)
    if match:
        return match.group(1)
    return None


def _fetch_rss_feed(blog_id: str) -> list:
    """RSS 피드 전체를 가져옵니다."""
    try:
        rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
        feed = feedparser.parse(rss_url)
        return feed.entries
    except Exception as e:
        print(f"    ⚠️ RSS 파싱 오류 ({blog_id}): {e}")
        return []


def _search_blogs_for_place(place_name: str, display: int = 30) -> list[dict]:
    """
    특정 가게명으로 네이버 블로그를 검색하고 RSS 매칭을 수행합니다.
    검색 범위를 넓혀(30개) RSS 매칭 성공률을 높이고, 5개만 찾으면 조기 종료합니다.
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []
    
    try:
        enc_text = urllib.parse.quote(place_name)
        # 검색 결과 풀을 30개로 대폭 확대 (RSS 매칭 확률 증가)
        url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_text}&display={display}"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
        
        response = urllib.request.urlopen(request)
        if response.getcode() != 200:
            return []
        
        result = json.loads(response.read().decode('utf-8'))
        items = result.get('items', [])
        matched_blogs = []
        
        # 블로그 ID별 RSS 캐싱 (같은 블로그의 여러 글을 처리할 때 효율적)
        blog_rss_cache = {}
        
        for item in items:
            # 목표 개수 5개를 채우면 즉시 종료 (속도 최적화)
            if len(matched_blogs) >= 5:
                break
                
            link = item.get('link', '')
            blog_id = _extract_blog_id(link)
            target_log_no = _get_log_no(link)
            
            if not blog_id or not target_log_no:
                continue
            
            # RSS 캐시 확인: 같은 블로그 ID의 RSS는 한 번만 가져오기
            if blog_id not in blog_rss_cache:
                blog_rss_cache[blog_id] = _fetch_rss_feed(blog_id)
            
            rss_entries = blog_rss_cache[blog_id]
            
            # RSS 엔트리에서 매칭되는 글 찾기
            for entry in rss_entries:
                entry_log_no = _get_log_no(entry.get('link', ''))
                if target_log_no == entry_log_no:
                    clean_desc = re.sub(r'<[^>]+>', '', entry.get('description', ''))
                    
                    matched_blogs.append({
                        "title": item.get('title', '').replace('<b>', '').replace('</b>', ''),
                        "link": link,
                        "full_content": clean_desc,
                        "bloggername": item.get('bloggername', ''),
                        "postdate": item.get('postdate', ''),
                        "rss_pub_date": entry.get('published', '')
                    })
                    break
        
        return matched_blogs
    except Exception as e:
        print(f"    ⚠️ 블로그 검색 중 오류: {e}")
        return []


def _enrich_place_with_blogs(place_data: dict) -> dict:
    """단일 가게 정보에 블로그 데이터를 추가합니다."""
    place_name = place_data.get('name', '')
    address = place_data.get('address', '')
    
    # 주소에서 주요 지역명 추출 (예: '광주광역시 동구 동명동' -> '광주 동명동')
    # Google Places API의 formattedAddress는 '대한민국'이 앞에 올 수 있음
    location_parts = address.split()
    
    # '대한민국' 제거
    if location_parts and location_parts[0] in ['대한민국', 'Republic', 'of', 'Korea']:
        location_parts = location_parts[1:]
    
    region_info = ""
    if len(location_parts) >= 2:
        # 시/도 + 동/읍/면 정도만 추출
        city_part = location_parts[0]
        # '광주광역시' -> '광주', '서울특별시' -> '서울' 등
        city = city_part.replace('특별시', '').replace('광역시', '').replace('자치시', '').replace('자치도', '')
        
        district = ""
        for part in location_parts[1:]:
            if any(part.endswith(suffix) for suffix in ['동', '읍', '면', '리']):
                district = part
                break
        
        if city and district:
            region_info = f"{city} {district}".strip()
        elif city:
            region_info = city
    
    # 검색어 조합: '지역명 + 가게명' (검색 정확도 향상)
    # 지역명이 없으면 가게명만 사용
    search_query = f"{region_info} {place_name}" if region_info else place_name
    
    # 디버그: 검색어 확인
    print(f"    🔍 검색어: '{search_query}' (주소: {address})")
    
    # display 인자 제거 (함수 기본값 30 사용)
    matched_blogs = _search_blogs_for_place(search_query)
    
    return {
        "place": place_data,
        "blogs": matched_blogs
    }


def naver_blog_search_node(state: AgentState) -> dict[str, Any]:
    """네이버 블로그 검색 및 RSS 매칭을 수행하는 노드입니다."""
    place_data_list = state.get("place_data")
    if not place_data_list:
        return {"enriched_results": None}
    
    print(f"\n🔗 Naver 블로그 검색 시작: {len(place_data_list)}개 가게")
    enriched_results = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_place = {
            executor.submit(_enrich_place_with_blogs, place): place
            for place in place_data_list
        }
        
        for future in as_completed(future_to_place):
            try:
                result = future.result()
                enriched_results.append(result)
                print(f"  📝 {result['place']['name']} - RSS 매칭 {len(result['blogs'])}/5개")
            except Exception as e:
                print(f"  ⚠️ 처리 오류: {e}")
    
    return {"enriched_results": enriched_results}
