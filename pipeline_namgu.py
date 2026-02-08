"""
남구 통합 파이프라인: RSS 수집 → 키워드 추출
입력: 남구_일반음식점_가게명_정제_권역별.json
출력:
  - rss_collected_남구_{권역}.jsonl   (RSS 원본)
  - extracted_keywords_남구_{권역}.json (키워드 추출 결과)

사용법:
  python pipeline_namgu.py                    # 전체 권역 실행
  python pipeline_namgu.py --region 백운·주월·월산권  # 특정 권역만
  python pipeline_namgu.py --step extract     # 키워드 추출만 (RSS 이미 수집됨)
"""

import os
import json
import asyncio
import aiohttp
import re
import time
import random
import urllib.parse
import argparse
import feedparser
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

# ============ Configuration ============
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")

INPUT_FILE = "남구_일반음식점_가게명_정제_권역별.json"
EXTRACT_MODEL = "gemini-3.0-flash-preview"

# 권역별 설정 (검색어 prefix - 구체적 동네명 사용)
REGION_CONFIG = {
    "백운·주월·월산권": {"prefixes": ["광주 백운동", "광주 주월동", "광주 월산동", "광주 남구"]},
    "봉선·진월·노대권": {"prefixes": ["광주 봉선동", "광주 진월동", "광주 노대동", "광주 남구"]},
    "양림·방림권":      {"prefixes": ["광주 양림동", "광주 방림동", "광주 남구"]},
    "효천·대촌권":      {"prefixes": ["광주 효천", "광주 대촌", "광주 남구"]},
}

# 키워드 추출 프롬프트 (14 카테고리)
EXTRACTION_PROMPT = """당신은 블로그 텍스트에서 **객관적 사실 정보**만 추출하는 전문가입니다.

## 규칙
- 주관적 평가(맛있다/예쁘다/좋다 등) 금지
- 본문에 '명시된 내용'만 추출 (추측 금지)
- 동일 의미는 가능한 한 표준 용어로 정규화

## 출력 형식 (반드시 아래 JSON 스키마)
{{
  "menu_type": ["메뉴 유형 (한식, 양식 등)"],
  "signature_menu": ["대표/시그니처 메뉴"],
  "price_info": ["가격 정보"],
  "ambiance": ["분위기 특징"],
  "interior": ["인테리어 특징"],
  "facilities": ["시설 (주차, 와이파이 등)"],
  "bathroom": ["화장실 정보"],
  "location": ["위치 정보"],
  "accessibility": ["접근성 정보"],
  "hours": ["영업시간/휴무일"],
  "service": ["서비스 특징"],
  "policy": ["정책 (예약, 노키즈존 등)"],
  "special_features": ["특이사항/특색"],
  "recommended_for": ["추천 대상/상황"]
}}

## 본문
{content}
"""

EMPTY_KEYWORDS = {
    "menu_type": [], "signature_menu": [], "price_info": [],
    "ambiance": [], "interior": [], "facilities": [], "bathroom": [],
    "location": [], "accessibility": [], "hours": [], "service": [],
    "policy": [], "special_features": [], "recommended_for": []
}


# ============================================================
# STEP 1: RSS 수집
# ============================================================

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

async def search_and_extract_rss(place_name, prefixes, display=100):
    # 검색 쿼리 다양화 - 동네명 + 가게이름, 가게이름 + 맛집/후기
    queries = []
    for prefix in prefixes:
        queries.append(f"{prefix} {place_name}")
    queries.append(f"광주 {place_name} 맛집")
    queries.append(f"광주 {place_name} 후기")
    # 중복 제거
    queries = list(dict.fromkeys(queries))

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }

    all_results = []
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=connector) as session:
        for query in queries:
            enc_text = urllib.parse.quote(query)
            url = f"https://openapi.naver.com/v1/search/blog.json?query={enc_text}&display={display}"

            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
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

                if len(all_results) >= 15:
                    break
            except Exception as e:
                print(f"  [RSS ERROR] {place_name}: {e}")

    unique_results = {r['link']: r for r in all_results}.values()
    return list(unique_results)

async def collect_rss_for_region(region_name: str, place_names: List[str], prefixes: List[str]):
    """특정 권역의 RSS 수집"""
    output_file = f"rss_collected_남구_{region_name}.jsonl"

    # 이미 처리된 가게 확인 (이어하기)
    processed_names = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        processed_names.add(item.get('place_name', ''))
                    except:
                        continue
        print(f"  [Resume] 이미 처리됨: {len(processed_names)}개")

    remaining = [p for p in place_names if p not in processed_names]
    print(f"  [RSS] 총: {len(place_names)}, 남은: {len(remaining)}")

    if not remaining:
        print(f"  [RSS] 이미 전부 완료!")
        return output_file

    batch_size = 10  # 쿼리 수 늘었으니 배치는 줄임
    start_time = time.time()

    for i in range(0, len(remaining), batch_size):
        batch = remaining[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(remaining) + batch_size - 1) // batch_size

        print(f"  [RSS Batch {batch_num}/{total_batches}] {len(batch)}개 처리 중...")

        tasks = [
            asyncio.create_task(
                _process_place_rss(name, prefixes)
            ) for name in batch
        ]
        results = await asyncio.gather(*tasks)

        # 매칭 통계 출력
        matched = sum(1 for r in results if r['filtered_count'] > 0)
        print(f"  [RSS Batch {batch_num}/{total_batches}] 매칭: {matched}/{len(batch)}")

        with open(output_file, 'a', encoding='utf-8') as f:
            for res in results:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")

        elapsed = time.time() - start_time
        done = len(processed_names) + i + len(batch)
        print(f"  [RSS Batch {batch_num}/{total_batches}] 저장 완료 ({done}/{len(place_names)}, {elapsed:.1f}s)")

        if i + batch_size < len(remaining):
            delay = random.uniform(3, 5)
            await asyncio.sleep(delay)

    # 최종 통계
    total_matched = 0
    total_posts = 0
    with open(output_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    item = json.loads(line)
                    if item.get('filtered_count', 0) > 0:
                        total_matched += 1
                    total_posts += item.get('filtered_count', 0)
                except:
                    pass
    rate = total_matched / len(place_names) * 100 if place_names else 0
    print(f"  [RSS] {region_name} 완료! 매칭률: {total_matched}/{len(place_names)} ({rate:.1f}%), 총 포스트: {total_posts}개")
    return output_file

async def _process_place_rss(place_name, prefixes):
    posts = await search_and_extract_rss(place_name, prefixes)
    # 날짜 필터 완화: 2024년 이후 포스트도 포함 (데이터 양 확보)
    filtered_posts = [p for p in posts if p.get('postdate', '') >= '20240101']
    return {
        "place_name": place_name,
        "posts": filtered_posts,
        "total_found": len(posts),
        "filtered_count": len(filtered_posts)
    }


# ============================================================
# STEP 2: 키워드 추출
# ============================================================

def create_llm():
    return ChatGoogleGenerativeAI(
        model=EXTRACT_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        max_output_tokens=2048,
    )

def extract_keywords_single(llm, content: str) -> Dict[str, List[str]]:
    """단일 블로그 본문에서 키워드 추출"""
    prompt = EXTRACTION_PROMPT.format(content=content[:3000])  # 토큰 절약

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content.strip()

        # markdown 코드블록 제거
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        result = json.loads(text)
        # 스키마 정규화
        normalized = {}
        for key in EMPTY_KEYWORDS:
            val = result.get(key, [])
            normalized[key] = val if isinstance(val, list) else []
        return normalized

    except Exception as e:
        return dict(EMPTY_KEYWORDS)

def merge_keywords(all_keywords: List[Dict]) -> Dict[str, List[str]]:
    """여러 포스트의 키워드를 병합 (중복 제거)"""
    merged = {k: set() for k in EMPTY_KEYWORDS}
    for kw in all_keywords:
        for key in EMPTY_KEYWORDS:
            items = kw.get(key, [])
            if isinstance(items, list):
                merged[key].update(items)
    return {k: sorted(list(v)) for k, v in merged.items()}

def extract_keywords_for_region(region_name: str, rss_file: str, place_names: List[str]):
    """특정 권역의 키워드 추출 (10개씩 배치)"""
    output_file = f"extracted_keywords_남구_{region_name}.json"

    # 이미 처리된 결과 로드 (이어하기)
    existing_places = {}
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            for p in existing_data.get("places", []):
                existing_places[p["place_name"]] = p
        print(f"  [Extract Resume] 이미 추출됨: {len(existing_places)}개")

    # RSS 데이터 로드
    rss_map = {}
    if os.path.exists(rss_file):
        with open(rss_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        rss_map[item["place_name"]] = item.get("posts", [])
                    except:
                        continue

    llm = create_llm()
    print(f"  [Extract] LLM 초기화 완료 ({EXTRACT_MODEL})")

    # 처리 대상: RSS에 포스트가 있고, 아직 추출 안 된 가게
    to_process = []
    for name in place_names:
        if name in existing_places:
            continue
        posts = rss_map.get(name, [])
        to_process.append((name, posts))

    print(f"  [Extract] 총: {len(place_names)}, 남은: {len(to_process)}")

    all_results = list(existing_places.values())  # 기존 결과 유지
    batch_size = 10
    start_time = time.time()

    for i in range(0, len(to_process), batch_size):
        batch = to_process[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(to_process) + batch_size - 1) // batch_size

        names_preview = [b[0] for b in batch[:3]]
        print(f"  [Extract Batch {batch_num}/{total_batches}] {', '.join(names_preview)}{'...' if len(batch) > 3 else ''}")

        for name, posts in batch:
            if not posts:
                # 포스트 없으면 빈 키워드
                all_results.append({
                    "place_name": name,
                    "keywords": {},
                    "analyzed_post_count": 0
                })
                continue

            # 각 포스트에서 키워드 추출 (최대 7개 → 키워드 풍부하게)
            post_keywords = []
            for post in posts[:7]:
                content = post.get("full_content", "")
                if len(content) < 50:
                    continue
                kw = extract_keywords_single(llm, content)
                post_keywords.append(kw)
                time.sleep(0.5)  # rate limit

            if post_keywords:
                merged = merge_keywords(post_keywords)
            else:
                merged = {}

            all_results.append({
                "place_name": name,
                "keywords": merged,
                "analyzed_post_count": len(post_keywords)
            })

        # 배치마다 중간 저장
        _save_extracted(output_file, region_name, all_results, start_time)
        elapsed = time.time() - start_time
        print(f"  [Extract Batch {batch_num}/{total_batches}] 저장 ({len(all_results)}/{len(place_names)}, {elapsed:.1f}s)")

    print(f"  [Extract] {region_name} 추출 완료! ({time.time() - start_time:.1f}s)")
    return output_file

def _save_extracted(output_file, region_name, places, start_time):
    """중간 저장"""
    output = {
        "region": f"남구_{region_name}",
        "metadata": {
            "model": EXTRACT_MODEL,
            "total_places": len(places),
            "processed_count": len(places),
            "elapsed_seconds": round(time.time() - start_time, 1),
            "mode": "incremental_save"
        },
        "places": places
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


# ============================================================
# Main
# ============================================================

async def run_pipeline(target_region: str = None, step: str = "all"):
    print("=" * 60)
    print("  남구 통합 파이프라인: RSS 수집 → 키워드 추출")
    print("=" * 60)

    # 입력 파일 로드
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    regions = list(data.keys())
    print(f"권역 목록: {regions}\n")

    if target_region:
        if target_region not in data:
            print(f"[ERROR] '{target_region}' 없음. 가능한 권역: {regions}")
            return
        regions = [target_region]

    for region_name in regions:
        place_names = data[region_name]
        config = REGION_CONFIG.get(region_name, {"prefixes": ["광주 남구"]})
        prefixes = config["prefixes"]

        print(f"\n{'='*60}")
        print(f"[{region_name}] 가게 수: {len(place_names)}")
        print(f"  검색 prefix: {prefixes}")
        print(f"{'='*60}")

        rss_file = f"rss_collected_남구_{region_name}.jsonl"

        # STEP 1: RSS 수집
        if step in ("all", "rss"):
            rss_file = await collect_rss_for_region(region_name, place_names, prefixes)

        # STEP 2: 키워드 추출
        if step in ("all", "extract"):
            extract_keywords_for_region(region_name, rss_file, place_names)

    print(f"\n{'='*60}")
    print("전체 파이프라인 완료!")
    print("출력 파일:")
    for region_name in regions:
        rss_f = f"rss_collected_남구_{region_name}.jsonl"
        kw_f = f"extracted_keywords_남구_{region_name}.json"
        rss_exists = "O" if os.path.exists(rss_f) else "X"
        kw_exists = "O" if os.path.exists(kw_f) else "X"
        print(f"  [{rss_exists}] {rss_f}")
        print(f"  [{kw_exists}] {kw_f}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="남구 RSS + 키워드 추출 파이프라인")
    parser.add_argument("--region", type=str, default=None,
                        help="특정 권역만 실행 (예: 백운·주월·월산권)")
    parser.add_argument("--step", type=str, default="all",
                        choices=["all", "rss", "extract"],
                        help="실행할 단계 (all/rss/extract)")
    args = parser.parse_args()

    asyncio.run(run_pipeline(target_region=args.region, step=args.step))
