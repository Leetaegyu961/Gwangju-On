"""
Mini Agent - Naver Blog Search
Naver 블로그 검색 + RSS 매칭으로 블로그 본문을 수집합니다.
"""

import asyncio
import aiohttp
import feedparser
import re
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urljoin

from .config import config


# 블로그 검색 설정
BLOG_DISPLAY = 100  # 100개 검색
RSS_MAX_MATCH = 5   # RSS 5개 매칭


async def search_blogs_for_place(place_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    장소 정보를 받아 관련 블로그를 검색하고 RSS 매칭된 결과를 반환합니다.
    
    Args:
        place_data: Place API에서 받은 장소 정보
        
    Returns:
        장소 정보 + 블로그 리스트
    """
    if not config.NAVER_CLIENT_ID or not config.NAVER_CLIENT_SECRET:
        print("⚠️ Naver API 키가 설정되지 않았습니다.")
        return {"place": place_data, "blogs": []}
    
    place_name = place_data.get("name", "")
    address = place_data.get("address", "")
    
    # 지역명 추출
    location_parts = address.split()
    city = ""
    district = ""
    
    if location_parts:
        city = location_parts[0].replace("특별시", "").replace("광역시", "")
        for part in location_parts[1:]:
            if any(part.endswith(suffix) for suffix in ["동", "읍", "면", "리"]):
                district = part
                break
    
    region = f"{city} {district}".strip() if (city and district) else city
    query = f"{region} {place_name}".strip()
    
    print(f"  🔍 블로그 검색: '{query}'")
    
    async with aiohttp.ClientSession() as session:
        blogs = await _search_and_match_rss(session, query)
        
    print(f"  📝 {place_name} - RSS 매칭 {len(blogs)}/{RSS_MAX_MATCH}개 완료")
    
    return {"place": place_data, "blogs": blogs}


async def enrich_places_with_blogs(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    여러 장소에 대해 블로그 검색을 병렬로 수행합니다.
    
    Args:
        places: 장소 정보 리스트
        
    Returns:
        장소 + 블로그 정보가 결합된 리스트
    """
    if not places:
        return []
    
    print(f"\n🔗 Naver 블로그 검색 시작: {len(places)}개 장소")
    
    tasks = [search_blogs_for_place(place) for place in places]
    results = await asyncio.gather(*tasks)
    
    return results


async def _search_and_match_rss(
    session: aiohttp.ClientSession, 
    query: str
) -> List[Dict[str, Any]]:
    """Naver API 검색 후 RSS 매칭"""
    enc_query = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_query}&display={BLOG_DISPLAY}&sort=date"
    
    headers = {
        "X-Naver-Client-Id": config.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET,
    }
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return []
            data = await response.json()
            items = data.get("items", [])
    except Exception as e:
        print(f"⚠️ Naver 검색 오류: {e}")
        return []
    
    if not items:
        return []
    
    matched_blogs = []
    blog_rss_cache = {}
    
    for item in items:
        if len(matched_blogs) >= RSS_MAX_MATCH:
            break
        
        result = await _process_blog_item(session, item, blog_rss_cache)
        if result:
            matched_blogs.append(result)
    
    return matched_blogs


async def _process_blog_item(
    session: aiohttp.ClientSession,
    item: dict,
    blog_rss_cache: dict
) -> Optional[dict]:
    """개별 블로그 아이템 처리 및 RSS 매칭"""
    link = item.get("link", "")
    
    # naver.me 단축 링크 해제
    if "naver.me" in link:
        resolved = await _resolve_shortlink(session, link)
        if resolved:
            link = resolved
    
    blog_id, log_no = _parse_blog_link(link)
    if not blog_id or not log_no:
        return None
    
    # RSS 피드 가져오기 (캐싱)
    if blog_id not in blog_rss_cache:
        blog_rss_cache[blog_id] = await _fetch_rss_feed(session, blog_id)
    
    rss_entries = blog_rss_cache.get(blog_id, [])
    if not rss_entries:
        return None
    
    # RSS에서 매칭되는 글 찾기
    for entry in rss_entries:
        entry_link = entry.get("link", "")
        _, entry_log_no = _parse_blog_link(entry_link)
        
        if entry_log_no and log_no == entry_log_no:
            clean_desc = re.sub(r"<[^>]+>", "", entry.get("description", ""))
            
            return {
                "title": item.get("title", "").replace("<b>", "").replace("</b>", ""),
                "link": link,
                "full_content": clean_desc,
                "bloggername": item.get("bloggername", ""),
                "postdate": item.get("postdate", ""),
            }
    
    return None


async def _fetch_rss_feed(session: aiohttp.ClientSession, blog_id: str) -> List[Any]:
    """RSS 피드 가져오기"""
    rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0",
        "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        async with session.get(rss_url, headers=headers, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                loop = asyncio.get_running_loop()
                feed = await loop.run_in_executor(None, feedparser.parse, xml_data)
                return feed.entries
    except Exception:
        pass
    
    return []


async def _resolve_shortlink(session: aiohttp.ClientSession, short_url: str) -> Optional[str]:
    """naver.me 단축 링크 해제"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0",
    }
    
    url = short_url
    try:
        for _ in range(3):  # 최대 3번 리다이렉트 추적
            async with session.get(url, headers=headers, timeout=5, allow_redirects=False) as resp:
                if resp.status in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("Location")
                    if loc:
                        url = urljoin(url, loc)
                        continue
                return str(resp.url) if resp.url else None
    except Exception:
        pass
    
    return None


def _parse_blog_link(url: str) -> Tuple[Optional[str], Optional[str]]:
    """네이버 블로그 URL에서 (blog_id, logNo) 추출"""
    if not url:
        return None, None
    
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower()
        path = p.path or ""
        qs = parse_qs(p.query or "")
    except Exception:
        return None, None
    
    if "naver.me" in host:
        return None, None
    
    blog_id = None
    log_no = None
    
    # Query param 기반
    if "blogId" in qs:
        blog_id = (qs.get("blogId") or [None])[0]
    if "logNo" in qs:
        log_no = (qs.get("logNo") or [None])[0]
    
    # Path 기반: /{blogId}/{logNo}
    segs = [s for s in path.split("/") if s]
    if segs:
        if segs[0].lower() != "postview.naver":
            if blog_id is None:
                blog_id = segs[0]
            if log_no is None:
                for s in segs[1:]:
                    if re.fullmatch(r"\d{8,}", s):
                        log_no = s
                        break
    
    # 정리
    if blog_id and blog_id.lower().endswith(".naver"):
        blog_id = None
    if log_no and not re.fullmatch(r"\d{8,}", log_no):
        log_no = None
    
    return blog_id, log_no
