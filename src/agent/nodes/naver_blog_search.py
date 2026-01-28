"""
Naver Blog Search Node (Async Version - Native)
Google Places 결과의 각 가게명으로 네이버 블로그를 검색하고 RSS 매칭된 항목만 수집합니다.
완전한 비동기(Native Async) 방식으로 구현되어 있습니다.
"""

import os
import re
import urllib.parse
import json
import asyncio
import aiohttp
import feedparser
from typing import Any, List, Dict, Optional
from dotenv import load_dotenv
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


async def _fetch_rss_feed(session: aiohttp.ClientSession, blog_id: str) -> List[Any]:
    """RSS 피드 전체를 비동기로 가져옵니다."""
    rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
    try:
        async with session.get(rss_url, timeout=5) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                return feed.entries
    except Exception as e:
        pass
    return []


async def _process_single_blog_item(
    session: aiohttp.ClientSession, 
    item: dict, 
    blog_rss_cache: dict
) -> Optional[dict]:
    """개별 블로그 아이템 하나를 처리합니다."""
    link = item.get('link', '')
    blog_id = _extract_blog_id(link)
    target_log_no = _get_log_no(link)
    
    if not blog_id or not target_log_no:
        return None
    
    if blog_id not in blog_rss_cache:
        blog_rss_cache[blog_id] = await _fetch_rss_feed(session, blog_id)
    
    rss_entries = blog_rss_cache.get(blog_id, [])
    
    for entry in rss_entries:
        entry_log_no = _get_log_no(entry.get('link', ''))
        if target_log_no == entry_log_no:
            clean_desc = re.sub(r'<[^>]+>', '', entry.get('description', ''))
            
            return {
                "title": item.get('title', '').replace('<b>', '').replace('</b>', ''),
                "link": link,
                "full_content": clean_desc,
                "bloggername": item.get('bloggername', ''),
                "postdate": item.get('postdate', ''),
                "rss_pub_date": entry.get('published', '')
            }
    return None


async def _search_blogs_for_place_async(session: aiohttp.ClientSession, query: str) -> List[dict]:
    """특정 쿼리로 네이버 검색 후 결과(RSS 매칭) 반환"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []
    
    try:
        enc_text = urllib.parse.quote(query)
        # 검색 결과 50개 조회
        url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_text}&display=50"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return []
            data = await response.json()
            items = data.get('items', [])
            
        if not items:
            return []
            
        matched_blogs = []
        blog_rss_cache = {}
        
        tasks = [
            asyncio.create_task(_process_single_blog_item(session, item, blog_rss_cache))
            for item in items
        ]
        
        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                if result:
                    matched_blogs.append(result)
                    if len(matched_blogs) >= 10:
                        break
            except Exception:
                pass
        
        for t in tasks:
            if not t.done():
                t.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
            
        return matched_blogs

    except Exception as e:
        print(f"    ⚠️ 블로그 검색 중 오류: {e}")
        return []


async def _enrich_place_with_blogs_async(session: aiohttp.ClientSession, place_data: dict) -> dict:
    """단일 가게 정보에 대해 여러 검색어 전략을 사용하여 블로그 데이터를 수집"""
    place_name = place_data.get('name', '')
    original_name = place_data.get('original_name', '')
    address = place_data.get('address', '')
    
    # 1. 지역명 추출 (동명동 등)
    location_parts = address.split()
    if location_parts and location_parts[0] in ['대한민국', 'Republic', 'of', 'Korea']:
        location_parts = location_parts[1:]
    
    city = ""
    if len(location_parts) >= 1:
        city = location_parts[0].replace('특별시', '').replace('광역시', '').replace('자치시', '').replace('자치도', '')
    
    district = ""
    for part in location_parts[1:]:
        if any(part.endswith(suffix) for suffix in ['동', '읍', '면', '리']):
            district = part
            break
            
    region_info = f"{city} {district}".strip() if (city and district) else city
    
    # 2. 검색어 후보 생성 (우선순위 순)
    search_queries = []
    
    # (1) 기본: "동명동 투에프"
    search_queries.append(f"{region_info} {place_name}".strip())
    
    # (2) 특수문자 제거: "데일리오아시스,광주점" -> "데일리오아시스 광주점"
    clean_name = re.sub(r'[^\w\s]', ' ', place_name).strip()
    clean_name = re.sub(r'\s+', ' ', clean_name) # 중복 공백 제거
    if clean_name != place_name:
        search_queries.append(f"{region_info} {clean_name}".strip())
        
    # (3) 원본 이름 (Google Original): "동명동 2F"
    if original_name and original_name != place_name:
        search_queries.append(f"{region_info} {original_name}".strip())
        
    # (4) 그냥 이름만 (지역명 없이, 너무 결과 안나올 때 대비 - 이건 위험하니 제외하거나 최후수단)
    # search_queries.append(place_name)

    # 중복 쿼리 제거
    unique_queries = []
    seen = set()
    for q in search_queries:
        if q not in seen:
            unique_queries.append(q)
            seen.add(q)
            
    print(f"  🔍 검색 전략 [{place_name}]: {unique_queries}")
    
    final_matched_blogs = []
    seen_links = set()
    
    for query in unique_queries:
        if len(final_matched_blogs) >= 10:
            break
            
        print(f"    👉 시도: '{query}'")
        matched = await _search_blogs_for_place_async(session, query)
        
        for blog in matched:
            if blog['link'] not in seen_links:
                final_matched_blogs.append(blog)
                seen_links.add(blog['link'])
                if len(final_matched_blogs) >= 10:
                    break
        
        if len(final_matched_blogs) >= 3: # 3개 이상이면 충분하다고 판단
            break
            
    print(f"  📝 {place_name} - 최종 RSS 매칭 {len(final_matched_blogs)}/10개 완료")
    
    return {
        "place": place_data,
        "blogs": final_matched_blogs
    }


async def _run_all_searches(place_data_list: List[dict]) -> List[dict]:
    """모든 가게에 대해 비동기 검색을 수행하는 메인 루틴"""
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            _enrich_place_with_blogs_async(session, place)
            for place in place_data_list
        ]
        return await asyncio.gather(*tasks)


async def naver_blog_search_node(state: AgentState) -> dict[str, Any]:
    """네이버 블로그 검색 및 RSS 매칭을 수행하는 노드입니다. (Native Async)"""
    place_data_list = state.get("place_data")
    if not place_data_list:
        return {"enriched_results": None}
    
    print(f"\n🔗 Naver 블로그 검색 시작 (Async): {len(place_data_list)}개 가게")
    
    try:
        enriched_results = await _run_all_searches(place_data_list)
    except Exception as e:
        print(f"⚠️ 비동기 실행 오류 발생: {e}")
        enriched_results = []
    
    return {"enriched_results": enriched_results}
