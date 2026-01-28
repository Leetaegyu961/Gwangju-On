import os
import urllib.parse
import json
import asyncio
import aiohttp
import re
import feedparser
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# --- Helper Functions (copied from naver_blog_search.py for standalone test) ---
def _get_log_no(url: str) -> str | None:
    match = re.search(r'/(\d{10,})', url)
    return match.group(1) if match else None

def _extract_blog_id(url: str) -> str | None:
    match = re.search(r'blog\.naver\.com/([^/]+)', url)
    if match: return match.group(1)
    match = re.search(r'm\.blog\.naver\.com/([^/]+)', url)
    return match.group(1) if match else None

async def _fetch_rss_feed(session, blog_id):
    rss_url = f"https://rss.blog.naver.com/{blog_id}.xml"
    try:
        async with session.get(rss_url, timeout=5) as response:
            if response.status == 200:
                xml_data = await response.text()
                return feedparser.parse(xml_data).entries
    except:
        pass
    return []

async def _process_single_item(session, item, cache):
    link = item.get('link', '')
    blog_id = _extract_blog_id(link)
    log_no = _get_log_no(link)
    
    if not blog_id or not log_no:
        return None  # URL 파싱 실패 또는 네이버 블로그 아님
    
    if blog_id not in cache:
        cache[blog_id] = await _fetch_rss_feed(session, blog_id)
    
    entries = cache.get(blog_id, [])
    for entry in entries:
        if _get_log_no(entry.get('link', '')) == log_no:
            # 매칭 성공! 본문 추출
            clean_desc = re.sub(r'<[^>]+>', '', entry.get('description', ''))
            return {
                "title": item.get('title', '').replace('<b>', '').replace('</b>', ''),
                "link": link,
                "full_content": clean_desc, # 전체 저장
                "content_length": len(clean_desc),
                "postdate": item.get('postdate', '')
            }
    return None # RSS 피드 내에 해당 글이 없음 (최신글 50개 밖이거나 비공개)

# --- Main Test Logic ---
async def test_max_rss_yield():
    print("="*60)
    print("🧪 네이버 검색 결과 100개 중 RSS 매칭 성공 개수 측정")
    print("="*60)
    
    # query = "동명동 맛집"  # 가장 일반적인 키워드
    query = "광주 동명동 2F" # 특정 가게
    
    print(f"📡 검색어: '{query}'")
    print("📡 요청: display=100 (API 최대치)")
    
    enc_text = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_text}&display=100"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    connector = aiohttp.TCPConnector(limit=50) # 동시성 높임
    async with aiohttp.ClientSession(connector=connector) as session:
        # 1. API 검색
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"❌ API 오류: {response.status}")
                return
            data = await response.json()
            items = data.get('items', [])
            total_items = len(items)
            print(f"✅ 검색 결과 수신: {total_items}개")
            
        if not items:
            return

        # 2. RSS 매칭 (All 100 items)
        print("🚀 RSS 병렬 매칭 시작 (제한 없음)...")
        
        rss_cache = {}
        tasks = [
            asyncio.create_task(_process_single_item(session, item, rss_cache))
            for item in items
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 3. 결과 분석
        matched_results = [r for r in results if r is not None]
        success_count = len(matched_results)
        
        print("\n" + "="*60)
        print(f"📊 최종 결과 리포트")
        print("="*60)
        print(f"🔹 검색 된 블로그 글: {total_items}개")
        print(f"🔹 RSS 본문 확보 성공: {success_count}개")
        print(f"🔹 성공률: {success_count/total_items*100:.1f}%")
        print("="*60)
        
        # 상세 결과 저장
        output = {
            "query": query,
            "total_searched": total_items,
            "success_count": success_count,
            "success_rate": f"{success_count/total_items*100:.1f}%",
            "matched_posts": matched_results
        }
        
        filename = "rss_yield_test.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        print(f"💾 결과 저장 완료: {filename}")

if __name__ == "__main__":
    asyncio.run(test_max_rss_yield())
