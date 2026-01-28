import os
import urllib.parse
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

async def debug_2f_search():
    print("🔎 '투에프' 검색 결과 상세 분석")
    
    place_name = "900달러"
    query = f"광주 동명동 {place_name}"
    enc_text = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_text}&display=10"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"❌ 검색 API 오류: {response.status}")
                return
            
            data = await response.json()
            items = data.get('items', [])
            
            print(f"✅ 검색어: '{query}' -> 결과 수: {len(items)}개")
            
            for i, item in enumerate(items, 1):
                title = item.get('title', '').replace('<b>', '').replace('</b>', '')
                link = item.get('link', '')
                print(f"\n{i}. {title}")
                print(f"   🔗 {link}")
                
                # 정규식 테스트
                import re
                log_no = None
                blog_id = None
                
                # logNo 추출
                match = re.search(r'/(\d{10,})', link)
                if match: log_no = match.group(1)
                
                # Blog ID 추출
                match = re.search(r'blog\.naver\.com/([^/]+)', link)
                if match: blog_id = match.group(1)
                elif re.search(r'm\.blog\.naver\.com/([^/]+)', link):
                    match = re.search(r'm\.blog\.naver\.com/([^/]+)', link)
                    blog_id = match.group(1)

                print(f"   🧩 파싱 결과: ID={blog_id}, LogNo={log_no}")
                if not blog_id or not log_no:
                    print("   ❌ 파싱 실패 (RSS 매칭 불가 원인)")

if __name__ == "__main__":
    if not NAVER_CLIENT_ID:
        print("❌ .env 설정이 필요합니다.")
    else:
        asyncio.run(debug_2f_search())
