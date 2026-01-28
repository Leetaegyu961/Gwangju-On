"""
Step 1: Naver API 블로그 검색 + RSS 본문 추출
- DongMyungDong_eat.json의 식당 리스트를 순회
- Naver Blog Search API로 검색
- RSS 피드로 본문 추출
- rss_collected.jsonl에 append 형태로 저장
"""

import os
import json
import asyncio
import aiohttp
import re
import time
import random
import urllib.parse
import feedparser
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
INPUT_LIST_FILE = "DongMyungDong_eat.json"
OUTPUT_JSONL_FILE = "rss_collected.jsonl"

# --- Helper Functions ---
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
        return None
    
    if blog_id not in cache:
        cache[blog_id] = await _fetch_rss_feed(session, blog_id)
    
    entries = cache.get(blog_id, [])
    for entry in entries:
        if _get_log_no(entry.get('link', '')) == log_no:
            clean_desc = re.sub(r'<[^>]+>', '', entry.get('description', ''))
            return {
                "title": item.get('title', '').replace('<b>', '').replace('</b>', ''),
                "link": link,
                "full_content": clean_desc,
                "content_length": len(clean_desc),
                "postdate": item.get('postdate', '')
            }
    return None

async def search_and_extract_rss(place_name, display=100):
    queries = [f"광주 동명동 {place_name}", f"동명동 {place_name}"]
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    all_results = []
    
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        for query in queries:
            print(f"   🔎 검색: '{query}'")
            enc_text = urllib.parse.quote(query)
            url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_text}&display={display}"
            
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        print(f"   ❌ API Error: {response.status}")
                        continue
                    data = await response.json()
                    items = data.get('items', [])
                
                if not items:
                    continue

                rss_cache = {}
                tasks = [
                    asyncio.create_task(_process_single_item(session, item, rss_cache))
                    for item in items
                ]
                results = await asyncio.gather(*tasks)
                valid_results = [r for r in results if r is not None]
                all_results.extend(valid_results)
                
                if len(all_results) >= 5:
                    break
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    unique_results = {r['link']: r for r in all_results}.values()
    return list(unique_results)

def load_processed_places() -> set:
    if not os.path.exists(OUTPUT_JSONL_FILE):
        return set()
    processed = set()
    with open(OUTPUT_JSONL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if 'place_name' in data:
                    processed.add(data['place_name'])
            except:
                pass
    return processed

async def main():
    # 1. Load targets
    with open(INPUT_LIST_FILE, 'r', encoding='utf-8') as f:
        place_names = json.load(f)
        
    processed = load_processed_places()
    print(f"📋 Total: {len(place_names)}, Already Done: {len(processed)}, Remaining: {len(place_names) - len(processed)}")

    # 2. Iterate
    for idx, place_name in enumerate(place_names):
        if place_name in processed:
            continue
            
        print(f"\n[{idx+1}/{len(place_names)}] {place_name}")
        
        # Search & RSS
        rss_posts = await search_and_extract_rss(place_name)
        
        # 2025년 이후 필터링
        valid_posts = [p for p in rss_posts if p.get('postdate', '') >= '20250101']
        print(f"   📰 RSS: {len(rss_posts)}개 -> 2025+: {len(valid_posts)}개")
        
        # Save to JSONL (Append)
        entry = {
            "place_name": place_name,
            "posts": valid_posts,
            "total_found": len(rss_posts),
            "filtered_count": len(valid_posts)
        }
        
        with open(OUTPUT_JSONL_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        print(f"   ✅ Saved to {OUTPUT_JSONL_FILE}")
        
        # Random Delay (30~50초)
        delay = random.uniform(30, 50)
        print(f"   💤 {delay:.0f}s...")
        time.sleep(delay)

if __name__ == "__main__":
    asyncio.run(main())
