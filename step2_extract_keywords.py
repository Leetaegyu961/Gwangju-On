"""
Step 2: LLM 키워드 추출 + Vertex AI용 JSONL 생성
- rss_collected.jsonl을 읽어서
- 각 가게별로 LLM 키워드 추출
- vertex_corpus.jsonl에 append 형태로 저장
"""

import os
import json
import time
from typing import List, Dict
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

# ============ Configuration ============
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

INPUT_JSONL_FILE = "rss_collected.jsonl"
OUTPUT_JSONL_FILE = "vertex_corpus.jsonl"


# ============ Schema ============
class ExtractedKeywords(BaseModel):
    facilities: List[str] = Field(default_factory=list)
    location: List[str] = Field(default_factory=list)
    hours: List[str] = Field(default_factory=list)
    menu_type: List[str] = Field(default_factory=list)
    signature_menu: List[str] = Field(default_factory=list)
    ambiance: List[str] = Field(default_factory=list)
    policy: List[str] = Field(default_factory=list)


EXTRACTION_PROMPT = """당신은 블로그 텍스트에서 **객관적 사실 정보**만 추출하는 전문가입니다.
- 주관적 평가(맛있다/예쁘다/좋다 등) 금지
- 본문에 '명시된 내용'만 추출 (추측 금지)
- 동일 의미는 가능한 한 표준 용어로 정규화 (예: 와이파이→무선 인터넷)

본문:
{content}
"""


# ============ Functions ============
def create_llm():
    base_llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        max_output_tokens=1024,
    )
    structured_llm = base_llm.with_structured_output(
        ExtractedKeywords,
        method="json_schema",
        include_raw=True,
    )
    return base_llm, structured_llm


def extract_keywords(structured_llm, base_llm, content: str) -> Dict:
    """단일 블로그 컨텐츠에서 키워드 추출"""
    prompt = EXTRACTION_PROMPT.format(content=content[:3000])  # 길이 제한
    
    empty_result = {
        "facilities": [], "location": [], "hours": [], 
        "menu_type": [], "signature_menu": [], "ambiance": [], "policy": []
    }
    
    try:
        result = structured_llm.invoke([HumanMessage(content=prompt)])
        parsing_error = result.get("parsing_error")
        parsed = result.get("parsed")

        if parsing_error is None and parsed is not None:
            return parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)
        
        # 복구 시도
        raw_msg = result.get("raw")
        raw_text = getattr(raw_msg, "content", "") if raw_msg else ""
        
        repair_prompt = f"""아래 출력은 스키마에 맞지 않거나 중간에 끊겼습니다.
반드시 아래 스키마에 맞는 '유효한 JSON'만 반환하세요.

스키마: {ExtractedKeywords.model_json_schema()}

깨진 출력: {raw_text}
"""
        repaired = base_llm.with_structured_output(
            ExtractedKeywords, method="json_schema", include_raw=False
        ).invoke([HumanMessage(content=repair_prompt)])

        if repaired is None:
            return empty_result
            
        return repaired.model_dump() if hasattr(repaired, "model_dump") else dict(repaired)

    except Exception as e:
        print(f"      ❌ LLM Error: {e}")
        return empty_result


def merge_keywords(posts_with_keywords: List[Dict]) -> Dict:
    """모든 포스트의 키워드를 병합"""
    merged = {
        "facilities": set(),
        "location": set(),
        "hours": set(),
        "menu_type": set(),
        "signature_menu": set(),
        "ambiance": set(),
        "policy": set(),
    }
    
    for post in posts_with_keywords:
        keywords = post.get("keywords", {})
        for category in merged.keys():
            items = keywords.get(category, [])
            if isinstance(items, list):
                merged[category].update(items)
    
    return {k: sorted(list(v)) for k, v in merged.items()}


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


def main():
    if not os.path.exists(INPUT_JSONL_FILE):
        print(f"❌ 입력 파일이 없습니다: {INPUT_JSONL_FILE}")
        print("   먼저 step1_collect_rss.py를 실행하세요.")
        return
    
    # Load all entries
    entries = []
    with open(INPUT_JSONL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                pass
    
    processed = load_processed_places()
    print(f"📋 Total: {len(entries)}, Already Done: {len(processed)}, Remaining: {len(entries) - len(processed)}")
    
    # Initialize LLM
    base_llm, structured_llm = create_llm()
    print("🤖 LLM Initialized")
    
    # Process each entry
    for idx, entry in enumerate(entries):
        place_name = entry.get('place_name', '')
        posts = entry.get('posts', [])
        
        if place_name in processed:
            continue
        
        if not posts:
            print(f"\n[{idx+1}/{len(entries)}] {place_name} - ⚠️ No posts, skipping")
            continue
            
        print(f"\n[{idx+1}/{len(entries)}] {place_name} ({len(posts)} posts)")
        
        # Extract keywords for each post
        posts_with_keywords = []
        for p_idx, post in enumerate(posts):
            print(f"   [{p_idx+1}/{len(posts)}] Extracting...")
            kws = extract_keywords(structured_llm, base_llm, post.get('full_content', ''))
            posts_with_keywords.append({
                "metadata": {
                    "title": post.get('title', ''),
                    "link": post.get('link', ''),
                    "postdate": post.get('postdate', '')
                },
                "keywords": kws
            })
            time.sleep(1)  # Rate limit
        
        # Merge keywords
        merged = merge_keywords(posts_with_keywords)
        
        # Create Vertex AI format
        vertex_entry = {
            "place_name": place_name,
            "merged_keywords_summary": merged,
            "metadata": [
                {"title": p["metadata"]["title"], "link": p["metadata"]["link"]}
                for p in posts_with_keywords
            ],
            "source_info": {
                "total_posts": len(posts_with_keywords)
            }
        }
        
        # Append to output
        with open(OUTPUT_JSONL_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(vertex_entry, ensure_ascii=False) + "\n")
        
        print(f"   ✅ Saved to {OUTPUT_JSONL_FILE}")


if __name__ == "__main__":
    main()
