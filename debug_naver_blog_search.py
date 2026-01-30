import argparse
import asyncio
import json
import os
import re
import urllib.parse
from typing import Any

import aiohttp
from dotenv import load_dotenv

from src.agent.nodes.naver_blog_search import (
    NAVER_BLOG_DISPLAY,
    NAVER_BLOG_SORT,
    NAVER_SHORTLINK_MAX_PER_PLACE,
    _fetch_rss_feed,
    _is_naver_me,
    _parse_naver_blog_link,
    _resolve_naver_me_shortlink,
)


def _log(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    print(json.dumps(payload, ensure_ascii=True))


def _build_queries(place_name: str, original_name: str, address: str) -> list[str]:
    location_parts = address.split()
    if location_parts and location_parts[0] in ["대한민국", "Republic", "of", "Korea"]:
        location_parts = location_parts[1:]

    city = ""
    if len(location_parts) >= 1:
        city = (
            location_parts[0]
            .replace("특별시", "")
            .replace("광역시", "")
            .replace("자치시", "")
            .replace("자치도", "")
        )

    district = ""
    for part in location_parts[1:]:
        if any(part.endswith(suffix) for suffix in ["구", "시", "면", "리"]):
            district = part
            break

    region_info = f"{city} {district}".strip() if (city and district) else city

    search_queries = []
    search_queries.append(f"{region_info} {place_name}".strip())

    clean_name = re.sub(r"[^\w\s]", " ", place_name).strip()
    clean_name = re.sub(r"\s+", " ", clean_name)
    if clean_name != place_name:
        search_queries.append(f"{region_info} {clean_name}".strip())

    if original_name and original_name != place_name:
        search_queries.append(f"{region_info} {original_name}".strip())

    return list(dict.fromkeys(search_queries))


async def _fetch_naver_blog_items(session: aiohttp.ClientSession, query: str) -> tuple[int, list[dict]]:
    enc_text = urllib.parse.quote(query)
    url = (
        "https://openapi.naver.com/v1/search/blog.json"
        f"?query={enc_text}&display={NAVER_BLOG_DISPLAY}&sort={NAVER_BLOG_SORT}"
    )

    headers = {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
    }

    _log("naver_api.request", query=query, url=url)
    async with session.get(url, headers=headers) as response:
        status = response.status
        if status != 200:
            _log("naver_api.response", query=query, status=status)
            return status, []
        data = await response.json()
        items = data.get("items", []) or []
        _log("naver_api.response", query=query, status=status, items=len(items))
        return status, items


async def _debug_process_single_blog_item(
    session: aiohttp.ClientSession,
    item: dict,
    blog_rss_cache: dict,
    shortlink_budget: dict,
    shortlink_budget_lock: asyncio.Lock,
    max_entry_logs: int,
) -> tuple[dict | None, str]:
    link = item.get("link", "")
    title = item.get("title", "")
    postdate = item.get("postdate", "")
    _log("item.start", title=title, link=link)

    if _is_naver_me(link):
        _log("item.shortlink", link=link, remaining=shortlink_budget.get("remaining", 0))
        resolved = await _resolve_naver_me_shortlink(
            session, link, shortlink_budget, shortlink_budget_lock
        )
        _log("item.shortlink.resolved", original=link, resolved=resolved)
        if resolved:
            link = resolved

    blog_id, target_log_no = _parse_naver_blog_link(link)
    _log("item.parsed", link=link, blog_id=blog_id, log_no=target_log_no, postdate=postdate)
    if not blog_id or not target_log_no:
        return None, "parse_failed"

    cached = blog_rss_cache.get(blog_id)
    if cached is None:
        blog_rss_cache[blog_id] = asyncio.create_task(_fetch_rss_feed(session, blog_id))
        cached = blog_rss_cache[blog_id]

    if isinstance(cached, asyncio.Task):
        rss_entries = await cached
        blog_rss_cache[blog_id] = rss_entries or []
    else:
        rss_entries = cached

    if not rss_entries:
        _log("rss.empty", blog_id=blog_id)
        return None, "rss_empty"

    log_nos = []
    log_no_ints = []
    for entry in rss_entries[:max_entry_logs]:
        entry_log_no = _parse_naver_blog_link(entry.get("link", ""))[1]
        if entry_log_no:
            log_nos.append(entry_log_no)
            if entry_log_no.isdigit():
                log_no_ints.append(int(entry_log_no))

    all_log_no_ints = []
    for entry in rss_entries:
        entry_log_no = _parse_naver_blog_link(entry.get("link", ""))[1]
        if entry_log_no and entry_log_no.isdigit():
            all_log_no_ints.append(int(entry_log_no))

    published_parsed = []
    published_raw = []
    for entry in rss_entries:
        if entry.get("published"):
            published_raw.append(entry.get("published"))
        if entry.get("published_parsed"):
            published_parsed.append(entry.get("published_parsed"))

    published_range = None
    if published_parsed:
        published_parsed_sorted = sorted(published_parsed)
        published_range = {
            "min": published_parsed_sorted[0],
            "max": published_parsed_sorted[-1],
        }

    log_no_range = None
    if all_log_no_ints:
        log_no_range = {"min": min(all_log_no_ints), "max": max(all_log_no_ints)}

    _log(
        "rss.fetched",
        blog_id=blog_id,
        entries=len(rss_entries),
        sample_log_nos=log_nos,
        log_no_range=log_no_range,
        published_range=published_range,
        published_samples=published_raw[:max_entry_logs],
    )

    for entry in rss_entries:
        entry_log_no = _parse_naver_blog_link(entry.get("link", ""))[1]
        if entry_log_no and target_log_no == entry_log_no:
            clean_desc = re.sub(r"<[^>]+>", "", entry.get("description", ""))
            result = {
                "title": title.replace("<b>", "").replace("</b>", ""),
                "link": link,
                "full_content": clean_desc,
                "bloggername": item.get("bloggername", ""),
                "postdate": item.get("postdate", ""),
                "rss_pub_date": entry.get("published", ""),
            }
            _log("item.matched", link=link, blog_id=blog_id, log_no=target_log_no)
            return result, "matched"

    _log("item.no_match", link=link, blog_id=blog_id, log_no=target_log_no)
    return None, "no_match"


async def run_debug(
    place_name: str,
    original_name: str,
    address: str,
    max_items: int,
    max_entry_logs: int,
) -> None:
    if not os.getenv("NAVER_CLIENT_ID") or not os.getenv("NAVER_CLIENT_SECRET"):
        _log("error.missing_env", required=["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"])
        return

    queries = _build_queries(place_name, original_name, address)
    _log("place.queries", place_name=place_name, original_name=original_name, address=address, queries=queries)

    shortlink_budget = {"remaining": NAVER_SHORTLINK_MAX_PER_PLACE}
    shortlink_budget_lock = asyncio.Lock()

    connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        final_matches = []
        seen_links = set()
        for query in queries:
            status, items = await _fetch_naver_blog_items(session, query)
            if status != 200:
                continue

            blog_rss_cache: dict[str, Any] = {}
            reasons = {"matched": 0, "parse_failed": 0, "rss_empty": 0, "no_match": 0}

            for idx, item in enumerate(items[:max_items], start=1):
                _log("item.index", query=query, index=idx, title=item.get("title", ""), link=item.get("link", ""))
                result, reason = await _debug_process_single_blog_item(
                    session,
                    item,
                    blog_rss_cache,
                    shortlink_budget,
                    shortlink_budget_lock,
                    max_entry_logs,
                )
                reasons[reason] = reasons.get(reason, 0) + 1

                if result and result["link"] not in seen_links:
                    final_matches.append(result)
                    seen_links.add(result["link"])
                    if len(final_matches) >= 5:
                        break

            _log("query.summary", query=query, **reasons)
            if len(final_matches) >= 5:
                break

    _log("final.summary", matched=len(final_matches), links=[b["link"] for b in final_matches])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug Naver blog RSS matching for a single place.")
    parser.add_argument("--name", default="Sample Cafe", help="Place name")
    parser.add_argument("--original-name", default="", help="Original name (optional)")
    parser.add_argument("--address", default="Gwangju", help="Place address")
    parser.add_argument("--max-items", type=int, default=10, help="Max items per query to inspect")
    parser.add_argument("--max-entry-logs", type=int, default=5, help="Sample RSS entry logNos to print")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = _parse_args()
    asyncio.run(
        run_debug(
            place_name=args.name,
            original_name=args.original_name,
            address=args.address,
            max_items=args.max_items,
            max_entry_logs=args.max_entry_logs,
        )
    )


if __name__ == "__main__":
    main()
