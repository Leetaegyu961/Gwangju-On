"""
블로그 컨텐츠에서 사실 기반 키워드 추출 스크립트

Gemini 3 Flash Preview 모델을 사용하여 블로그 full_content에서
주관적 표현이 아닌 객관적 사실(특징)을 키워드 형태로 추출합니다.
"""

import json
import os
import time
from typing import Any, Tuple, List, Dict
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

# ============ Configuration ============
# 환경 변수에서 API 키 로드
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")

# 모델 설정
MODEL_NAME = "gemini-3-flash-preview"

# 입력/출력 파일 경로
INPUT_FILE = "rss_yield_test.json"
OUTPUT_FILE = "extracted_keywords.json"


# ============ Schemas & Prompts ============

# ✅ 스키마 정의 (모델이 이 형태로만 출력하도록 제약)
class ExtractedKeywords(BaseModel):
    facilities: List[str] = Field(default_factory=list, description="시설 특징 (무선 인터넷, 주차장 등)")
    location: List[str] = Field(default_factory=list, description="위치 정보 (2층, 스타벅스 옆 등)")
    hours: List[str] = Field(default_factory=list, description="영업 정보 (영업시간, 휴무일 등)")
    menu_type: List[str] = Field(default_factory=list, description="메뉴 유형 (한식, 퓨전 등)")
    signature_menu: List[str] = Field(default_factory=list, description="대표 메뉴 이름")
    ambiance: List[str] = Field(default_factory=list, description="분위기 특징 (조명, 인테리어 등)")
    policy: List[str] = Field(default_factory=list, description="정책 (예약 가능, 노키즈존 등)")

# ✅ 프롬프트는 JSON 형식 지시를 빼도 됨(스키마가 강제하니까)
EXTRACTION_PROMPT = """당신은 블로그 텍스트에서 **객관적 사실 정보**만 추출하는 전문가입니다.
- 주관적 평가(맛있다/예쁘다/좋다 등) 금지
- 본문에 '명시된 내용'만 추출 (추측 금지)
- 동일 의미는 가능한 한 표준 용어로 정규화 (예: 와이파이→무선 인터넷)

본문:
{content}
"""


# ============ Functions ============

def load_matched_posts(file_path: str) -> list[dict]:
    """JSON 파일에서 매칭된 포스트 로드"""
    if not os.path.exists(file_path):
        print(f"❌ 입력 파일이 없습니다: {file_path}")
        return []
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    matched_posts = data.get("matched_posts", [])
    print(f"📚 {len(matched_posts)}개의 매칭된 블로그 포스트를 로드했습니다.")
    return matched_posts


def create_llm() -> Tuple[ChatGoogleGenerativeAI, Any]:
    base_llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        max_output_tokens=1024,
    )

    class ExtractedKeywords(BaseModel):
        facilities: List[str] = Field(default_factory=list)
        location: List[str] = Field(default_factory=list)
        hours: List[str] = Field(default_factory=list)
        menu_type: List[str] = Field(default_factory=list)
        signature_menu: List[str] = Field(default_factory=list)
        ambiance: List[str] = Field(default_factory=list)
        policy: List[str] = Field(default_factory=list)

    structured_llm = base_llm.with_structured_output(
        ExtractedKeywords,
        method="json_schema",
        include_raw=True,
    )

    return base_llm, structured_llm


def extract_keywords_from_content(structured_llm, base_llm, content: str) -> Dict[str, List[str]]:
    """단일 블로그 컨텐츠에서 키워드 추출 (Structured Output + 자동 복구 적용)"""
    prompt = EXTRACTION_PROMPT.format(content=content)

    try:
        # 1) 1차: structured output
        result = structured_llm.invoke([HumanMessage(content=prompt)])

        # include_raw=True면 dict로 옴: {raw, parsed, parsing_error}
        parsing_error = result.get("parsing_error")
        parsed = result.get("parsed")

        if parsing_error is None and parsed is not None:
            return parsed.model_dump() if hasattr(parsed, "model_dump") else dict(parsed)

        # 2) 실패 시: raw 텍스트 기반으로 "복구 1회"
        print("  ⚠️ Structured Output 파싱 실패, 복구 시도 중...")
        raw_msg = result.get("raw")
        raw_text = getattr(raw_msg, "content", "") if raw_msg else ""

        repair_prompt = f"""아래 출력은 스키마에 맞지 않거나 중간에 끊겼습니다.
반드시 아래 스키마에 맞는 '유효한 JSON'만 반환하세요. (설명/마크다운 금지)

스키마:
{ExtractedKeywords.model_json_schema()}

깨진 출력:
{raw_text}
"""

        repaired = base_llm.with_structured_output(
            ExtractedKeywords, method="json_schema", include_raw=False
        ).invoke([HumanMessage(content=repair_prompt)])

        if repaired is None:
            print("  ⚠️ 복구 실패: 모델이 유효한 JSON을 반환하지 않았습니다.")
            return {
                "facilities": [], "location": [], "hours": [], 
                "menu_type": [], "signature_menu": [], "ambiance": [], "policy": []
            }

        return repaired.model_dump() if hasattr(repaired, "model_dump") else dict(repaired)

    except Exception as e:
        print(f"  ❌ 상세 추출 실패: {e}")
        return {
            "facilities": [], "location": [], "hours": [], 
            "menu_type": [], "signature_menu": [], "ambiance": [], "policy": []
        }


def process_all_posts(base_llm, structured_llm, posts: list[dict]) -> list[dict]:
    """모든 블로그 포스트 처리"""
    results = []
    
    for idx, post in enumerate(posts, 1):
        title = post.get("title", "제목 없음")
        link = post.get("link", "")
        postdate = post.get("postdate", "")
        full_content = post.get("full_content", "")
        
        print(f"\n[{idx}/{len(posts)}] 처리 중: {title[:50]}...")
        
        # 키워드 추출
        keywords = extract_keywords_from_content(structured_llm, base_llm, full_content)
        
        # 결과 구성 (메타데이터 포함)
        result = {
            "metadata": {
                "title": title,
                "link": link,
                "postdate": postdate,
                "content_length": len(full_content),
            },
            "keywords": keywords,
        }
        
        results.append(result)
        
        # Rate limiting (Gemini API 제한 고려)
        time.sleep(1)
        
        # 추출된 키워드 미리보기 출력
        non_empty = {k: v for k, v in keywords.items() if v and isinstance(v, list)}
        if non_empty:
            print(f"  ✅ 추출된 키워드: {len(non_empty)} 카테고리")
            for category, kws in non_empty.items():
                if kws:
                    print(f"     - {category}: {', '.join(kws[:3])}{'...' if len(kws) > 3 else ''}")
    
    return results


def merge_keywords(results: list[dict]) -> dict[str, list[str]]:
    """모든 결과에서 키워드 병합 및 중복 제거"""
    merged = {
        "facilities": set(),
        "location": set(),
        "hours": set(),
        "menu_type": set(),
        "signature_menu": set(),
        "ambiance": set(),
        "policy": set(),
    }
    
    for result in results:
        keywords = result.get("keywords", {})
        for category in merged.keys():
            items = keywords.get(category, [])
            if isinstance(items, list):
                merged[category].update(items)
    
    # set -> list 변환
    return {k: sorted(list(v)) for k, v in merged.items()}


def save_results(results: list[dict], merged_keywords: dict, output_path: str):
    """결과 저장"""
    output = {
        "total_processed": len(results),
        "extraction_model": MODEL_NAME,
        "merged_keywords_summary": merged_keywords,
        "posts": results,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과가 {output_path}에 저장되었습니다.")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🔍 블로그 컨텐츠 키워드 추출기 (Structured Output)")
    print(f"   모델: {MODEL_NAME}")
    print("=" * 60)
    
    # 1. LLM 초기화
    base_llm, structured_llm = create_llm()
    print("✅ LLM 초기화 완료")
    
    # 2. 데이터 로드
    posts = load_matched_posts(INPUT_FILE)
    
    if not posts:
        print("❌ 처리할 포스트가 없습니다.")
        return
    
    # 3. 키워드 추출 처리
    print(f"\n🚀 {len(posts)}개 포스트에서 키워드 추출 시작...")
    results = process_all_posts(base_llm, structured_llm, posts)
    
    # 4. 키워드 병합
    print("\n📊 키워드 병합 중...")
    merged_keywords = merge_keywords(results)
    
    # 5. 병합 결과 출력
    print("\n" + "=" * 60)
    print("📋 병합된 키워드 요약:")
    print("=" * 60)
    for category, keywords in merged_keywords.items():
        if keywords:
            print(f"\n【{category}】 ({len(keywords)}개)")
            print(f"   {', '.join(keywords)}")
    
    # 6. 결과 저장
    save_results(results, merged_keywords, OUTPUT_FILE)
    
    print("\n✅ 키워드 추출 완료!")


if __name__ == "__main__":
    main()
