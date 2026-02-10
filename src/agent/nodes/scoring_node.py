"""
Scoring Node v4 (LLM 직접 점수화 - Batching 적용)
LLM이 4개 차원(맛/서비스/가성비/재방문)별로 직접 채점하는 방식입니다.
배치 처리(Batch Processing)를 통해 LLM 호출 수를 줄이고 속도를 개선했습니다.
"""

import os
import json
import asyncio
import time
import random
from typing import Any, List, Dict, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from ..state import AgentState
from ..scoring_system import get_scoring_system, PersonalizedScoringSystem, haversine_km, proximity_bonus
from ..config import config


# v4 Scoring Rubric (상세 평가 기준)
SCORING_RUBRIC = """
## 평가 기준 (Scoring Rubric)

### 1. 맛 (taste): 0~2점
| 점수 | 기준 | 키워드 예시 |
|------|------|-----------|
| 2.0 | 극찬 | "인생 맛집", "미쳤다", "존맛", "겉바속촉", "JMT", "레전드" |
| 1.5 | 호평 | "맛있다", "만족", "괜찮다", "추천" |
| 1.0 | 보통 | "무난", "그럭저럭", "평범" |
| 0.5 | 비호평 | "별로", "기대 이하", "쏘쏘" |
| 0.0 | 혹평 | "맛없다", "최악", "환불", "노맛" |

### 2. 서비스/분위기 (service): 0~2점
| 점수 | 기준 | 키워드 예시 |
|------|------|-----------|
| 2.0 | 극찬 | "친절 최고", "감성 터짐", "분위기 미쳤다", "인테리어 예술" |
| 1.5 | 호평 | "친절", "깔끔", "분위기 좋음", "청결" |
| 1.0 | 보통 | "그냥 그렇다", "무난" |
| 0.5 | 비호평 | "불친절", "시끄럽다", "더럽다" |
| 0.0 | 혹평 | "최악", "다신 안 감", "불쾌" |

### 3. 가성비 (value): 0~1점
| 점수 | 기준 | 키워드 예시 |
|------|------|-----------|
| 1.0 | 좋음 | "가성비 갑", "저렴", "푸짐", "양 많음", "합리적" |
| 0.5 | 보통 | "적당", "나쁘지 않음" |
| 0.0 | 나쁨 | "비쌈", "가격 대비 별로", "아깝다" |

### 4. 재방문 의사 (revisit): 0~1점
| 점수 | 기준 | 키워드 예시 |
|------|------|-----------|
| 1.0 | 있음 | "또 갈 것", "단골", "추천", "재방문", "꼭 가세요" |
| 0.5 | 애매 | "기회 되면", "한 번쯤" |
| 0.0 | 없음 | "안 갈 것", "한 번으로 충분", "비추" |

## 중요 지침
- 신조어/은어도 맥락으로 판단하세요 (예: "겉바속촉"=바삭하고 맛있음, "JMT"=존맛탱=매우 맛있음)
- 이모티콘/감탄사도 고려하세요 (예: "ㅋㅋㅋ", "!!!", "❤️" = 긍정)
- 리뷰가 없거나 부족하면 각 차원에 기본값 1.0점을 부여하세요
"""

def _get_default_score(reason: str) -> Tuple[float, Dict]:
    """기본 점수 반환"""
    default_breakdown = {
        "taste": 1.0,
        "service": 1.0,
        "value": 0.5,
        "revisit": 0.5,
        "total": 3.0,
        "reason": reason
    }
    return 3.0, default_breakdown


async def analyze_sentiment_batch(llm: ChatGoogleGenerativeAI, batch_items: List[Dict]) -> List[Tuple[float, Dict]]:
    """
    Process a batch of items (max 5) in a single LLM call.
    Returns a list of tuples (total_score, breakdown) corresponding to the input items.
    """
    # Prepare prompt data
    places_text = ""
    for idx, item in enumerate(batch_items):
        place = item.get("place", {})
        blogs = item.get("blogs", [])
        reviews = place.get("reviews", [])
        
        # Collect reviews
        blog_texts = []
        for blog in blogs[:3]:
            content = blog.get("full_content", "")[:300]  # Reduced length for batching
            if content:
                blog_texts.append(content)
        
        review_texts = []
        for review in reviews[:5]:
            text = review.get("text", "")[:150] # Reduced length for batching
            if text:
                review_texts.append(f"⭐{review.get('rating', 0)}: {text}")
        
        blog_summary = "\n".join(blog_texts) if blog_texts else "블로그 리뷰 없음"
        review_summary = "\n".join(review_texts) if review_texts else "Google 리뷰 없음"
        
        # Keywords Summary (from vector metadata)
        keywords = place.get("keywords", {})
        keywords_text = ""
        if keywords:
            # Flatten important keys
            important_keys = ["menu_type", "signature_menu", "ambiance", "special_features", "recommended_for"]
            lines = []
            for k in important_keys:
                if k in keywords and keywords[k]:
                    val = keywords[k]
                    if isinstance(val, list):
                        val = ", ".join(val)
                    lines.append(f"- {k}: {val}")
            if lines:
                keywords_text = "\n".join(lines)
        
        keywords_section = f"#### Key Attributes (Metadata)\n{keywords_text}" if keywords_text else "#### Key Attributes\n정보 없음"

        places_text += f"""
---
### Place {idx + 1}: {place.get('name', 'Unknown')}
{keywords_section}
#### Google Reviews
{review_summary}
#### Blog Reviews
{blog_summary}
"""

    prompt = f"""당신은 음식점 리뷰 전문 평가사입니다.
아래 {len(batch_items)}개의 음식점 리뷰를 읽고 각각 4가지 차원에서 점수를 매기세요.

{SCORING_RUBRIC}

## 평가 대상 목록
{places_text}

---

## 출력 형식 (JSON List Only)
반드시 아래 형식의 JSON 리스트만 출력하세요. 순서는 입력된 Place 1, Place 2... 순서를 지켜야 합니다.
**중요: reason은 반드시 30자 이내로 핵심만 간결하게 작성하세요. 긍정/부정 톤을 일관성 있게 유지하세요.**

[
  {{
    "index": 1,
    "name": "음식점 이름",
    "taste": 1.5,
    "service": 2.0,
    "value": 1.0,
    "revisit": 1.0,
    "reason": "맛과 분위기가 좋다는 평이 많음"
  }},
  ...
]
"""
    
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.strip().startswith("json"):
                content = content.strip()[4:].strip()
            else:
                content = content.strip()
        
        results_json = json.loads(content)
        
        # Process results
        batch_results = []
        
        if isinstance(results_json, list):
             # Ensure we have results for each item
            for i in range(len(batch_items)):
                # Try to find matching result by index or position
                result = None
                if i < len(results_json):
                    result = results_json[i]
                
                # If result is missing or structure is wrong, use default
                if not result:
                    batch_results.append(_get_default_score("분석 누락"))
                    continue
                
                # Calculate score
                taste = min(2.0, max(0.0, float(result.get("taste", 1.0))))
                service = min(2.0, max(0.0, float(result.get("service", 1.0))))
                value = min(1.0, max(0.0, float(result.get("value", 0.5))))
                revisit = min(1.0, max(0.0, float(result.get("revisit", 0.5))))
                reason = result.get("reason", "평가 완료")
                
                total_score = taste + service + value + revisit
                
                breakdown = {
                    "taste": round(taste, 1),
                    "service": round(service, 1),
                    "value": round(value, 1),
                    "revisit": round(revisit, 1),
                    "total": round(total_score, 2),
                    "reason": reason
                }
                batch_results.append((round(total_score, 2), breakdown))
        else:
             # Json parsed but not a list
            print(f"⚠️ [Batch Scoring] Expected list, got {type(results_json)}")
            return [_get_default_score("형식 오류") for _ in batch_items]

        return batch_results

    except Exception as e:
        print(f"⚠️ [Batch Scoring] LLM 분석 실패: {e}")
        return [_get_default_score("분석 실패 - 기본값 사용") for _ in batch_items]


async def scoring_node(state: AgentState) -> dict[str, Any]:
    """
    v4: enriched_results를 입력으로 받아 LLM 직접 채점을 수행하고 scored_results를 반환합니다.
    배치 처리를 적용하여 효율성을 높였습니다.
    
    Args:
        state: 현재 에이전트 상태 (enriched_results 포함)
        
    Returns:
        업데이트된 상태 {"scored_results": [...]}
    """
    enriched_results = state.get("enriched_results")
    
    if not enriched_results:
        print("⚠️ [Scoring Node] enriched_results가 없습니다.")
        return {"scored_results": None}
    
    print(f"\n📊 [Scoring Node v4] LLM 배치 채점 시작: {len(enriched_results)}개 음식점")
    
    # LLM 초기화
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.3,
    )
    
    # 사용자 프로필 조회 (Personalization)
    user_id = state.get("userId")
    user_profile = {}
    if user_id:
        try:
            from backend.db import get_database
            # Async DB call inside sync/async node
            db = await get_database()
            if db is not None:
                profile = await db["user_preferences"].find_one({"userId": user_id})
                if profile:
                    user_profile = profile
                    print(f"👤 [Scoring Node] User Profile Found: {user_id}")
            else:
                print(f"⚠️ [Scoring Node] DB not initialized. Skipping user profile fetch.")
        except Exception as e:
            print(f"⚠️ [Scoring Node] Failed to fetch user profile: {e}")

    # 스코어링 시스템 초기화
    base_dir = os.getcwd()
    data_dir = os.path.join(base_dir, "data")
    
    if user_profile:
        scoring_system = PersonalizedScoringSystem(data_dir, user_profile)
        
        # [New] 실시간 세션 테마 반영 (QueryPlanner가 생성한 Themes)
        session_themes = state.get("themes", [])
        if session_themes:
            scoring_system.set_session_themes(session_themes)
            print(f"🔥 [Scoring Node] Session Themes Applied (Real-time Context): {session_themes}")
            
    else:
        scoring_system = get_scoring_system(data_dir)
        # 세션 테마가 있어도 Personalized가 아니면 적용 불가할 수 있으나,
        # 기본 시스템에서도 테마 매칭을 원하면 PersonalizedScoringSystem을 기본으로 쓰되 profile을 비워도 됨.
        if state.get("themes"):
             scoring_system = PersonalizedScoringSystem(data_dir, {})
             scoring_system.set_session_themes(state.get("themes", []))
             print(f"🔥 [Scoring Node] Session Themes Applied (No User Profile): {state.get('themes')}")
    
    # 배치 처리 준비 (최적화: 배치 크기 증가로 LLM 호출 횟수 감소)
    batch_size = 5
    batches = [enriched_results[i:i + batch_size] for i in range(0, len(enriched_results), batch_size)]
    
    print(f"🤖 LLM 배치 채점 실행 중 ({len(batches)} 배치)...")
    
    # 비동기 병렬 실행 + 타이밍 측정
    t_scoring_start = time.time()
    tasks = [analyze_sentiment_batch(llm, batch) for batch in batches]
    batch_results = await asyncio.gather(*tasks)
    print(f"⏱️ [Scoring] LLM 배치 채점 완료: {time.time() - t_scoring_start:.2f}초")
    
    # 결과 평탄화 (Flatten)
    flat_sentiment_results = [item for sublist in batch_results for item in sublist]
    
    analyzed_results = []
    
    # 결과 합치기
    for item, (sentiment_score, sentiment_breakdown) in zip(enriched_results, flat_sentiment_results):
        place = item.get("place", {})
        
        if isinstance(scoring_system, PersonalizedScoringSystem):
            # 개인화 스코어링 (Base + Preference)
            # LLM 키워드를 태그로 활용하기 위해 주입
            item["llm_keywords"] = [k.strip() for k in sentiment_breakdown.get("reason", "").split(" ") if len(k) > 1]
            
            p_score, base_breakdown = scoring_system.calculate_final_score(item)
            
            # 감성 점수 추가 (Base + Preference + Sentiment)
            total_score = p_score + sentiment_score
            
            base_breakdown["sentiment"] = sentiment_score
            base_breakdown["sentiment_breakdown"] = sentiment_breakdown
            base_breakdown["sentiment_summary"] = sentiment_breakdown.get("reason", "")
            base_breakdown["final_total"] = round(total_score, 2)
            
        else:
            # 기본 스코어링
            base_score, base_breakdown = scoring_system.calculate_score(item)
            
            # 감성 점수 통합
            base_breakdown["sentiment"] = sentiment_score
            base_breakdown["sentiment_breakdown"] = sentiment_breakdown
            base_breakdown["sentiment_summary"] = sentiment_breakdown.get("reason", "")
            
            # 총점 = 기본 점수 + 감성 점수
            total_score = base_score + sentiment_score
        
        analyzed_results.append({
            **item,
            "score": round(total_score, 2),
            "score_breakdown": base_breakdown
        })

    # 점수 순으로 정렬
    analyzed_results.sort(key=lambda x: x["score"], reverse=True)
    
    # 결과 출력 (상위 3개)
    print(f"\n🏆 [Scoring Node v4] Top 3 결과:")
    for idx, item in enumerate(analyzed_results[:3], 1):
        place = item.get("place", {})
        score = item.get("score", 0)
        bd = item.get("score_breakdown", {})
        s_bd = bd.get("sentiment_breakdown", {})
        
        print(f"  {idx}. {place.get('name', 'Unknown')} - {score}점")
        print(f"     감성: {bd.get('sentiment', 0)}점 (맛:{s_bd.get('taste', 0)} 서비스:{s_bd.get('service', 0)} 가성비:{s_bd.get('value', 0)} 재방문:{s_bd.get('revisit', 0)})")
        print(f"     이유: {s_bd.get('reason', '')[:50]}...")
    
    print(f"\n✅ [Scoring Node v4] 스코어링 완료: {len(analyzed_results)}개 음식점")
    
    # ========================================
    # [v6] 코스 생성 (Slot-based + Weighted Sampling)
    # v5 문제: survey에서 설정한 코스 개수/타입 순서가 무시됨
    # 해결: survey courses를 "슬롯"으로 사용하여 타입별 매칭
    # ========================================
    themes = state.get("themes", ["맛집", "카페", "힐링"])

    # [FIX] survey에서 설정한 코스 구성 읽기
    survey_data = state.get("survey_data", {})
    survey_courses = []
    if isinstance(survey_data, dict):
        survey_courses = survey_data.get("courses", [])

    # 슬롯 타입 시퀀스 추출 (예: ["식당", "카페", "숙박", "식당"])
    slot_types = []
    for sc in survey_courses:
        if isinstance(sc, dict):
            slot_types.append(sc.get("type", ""))
        else:
            slot_types.append("")

    places_per_course = len(slot_types) if slot_types else 4
    print(f"[Scoring v6] 코스당 장소 수: {places_per_course}, 슬롯 타입: {slot_types}")

    # 테마별 키워드 매핑
    theme_keywords = {
        "데이트": ["데이트", "분위기", "로맨틱", "감성", "커플"],
        "맛집": ["맛집", "맛있", "인생맛집", "JMT", "존맛"],
        "카페": ["카페", "디저트", "커피", "베이커리"],
        "디저트": ["디저트", "케이크", "빙수", "달콤"],
        "뷰맛집": ["뷰", "전망", "야경", "통유리", "탁트인"],
        "힐링": ["힐링", "조용", "편안", "휴식"],
        "가성비": ["가성비", "저렴", "푸짐", "합리적"],
    }

    # 타입 매칭 키워드 (survey 타입 → 장소 속성 매칭)
    TYPE_MATCH_KEYWORDS = {
        "식당": ["식당", "맛집", "한식", "일식", "중식", "양식", "분식", "고기", "국밥", "restaurant", "food"],
        "카페": ["카페", "커피", "디저트", "베이커리", "빵", "케이크", "cafe", "coffee"],
        "놀거리": ["놀거리", "체험", "관광", "공원", "전시", "문화", "레저", "activity"],
        "숙박": ["숙박", "호텔", "펜션", "게스트하우스", "모텔", "hotel", "lodging"],
    }

    CANDIDATE_POOL_SIZE = 10
    EXPLORATION_WEIGHT = 0.4

    generated_courses = []
    used_place_ids = set()

    for theme_idx, theme in enumerate(themes[:3]):
        keywords = theme_keywords.get(theme, [theme])

        # 모든 후보에 테마 점수 부여
        scored_for_theme = []
        for item in analyzed_results:
            if item.get("place", {}).get("id") in used_place_ids:
                continue

            place = item.get("place", {})
            base_score = item.get("score", 0)

            theme_bonus = 0
            reason_text = item.get("score_breakdown", {}).get("sentiment_summary", "")
            place_keywords = place.get("keywords", {})

            matched_kw = set()
            for kw in keywords:
                if kw in reason_text and kw not in matched_kw:
                    theme_bonus += 2.0
                    matched_kw.add(kw)
                for v in place_keywords.values():
                    if isinstance(v, str) and kw in v and kw not in matched_kw:
                        theme_bonus += 1.5
                        matched_kw.add(kw)
                    elif isinstance(v, list):
                        for item_v in v:
                            if kw in str(item_v) and kw not in matched_kw:
                                theme_bonus += 1.0
                                matched_kw.add(kw)

            noise = random.uniform(0, EXPLORATION_WEIGHT * base_score) if base_score > 0 else 0

            # 장소의 추론 타입 미리 계산
            inferred_type = _infer_place_type(place)

            scored_for_theme.append({
                **item,
                "theme_score": base_score + theme_bonus + noise,
                "inferred_type": inferred_type
            })

        scored_for_theme.sort(key=lambda x: x["theme_score"], reverse=True)

        # [v6] 슬롯 기반 선택: 각 슬롯의 타입에 맞는 장소를 선택
        selected_places = []

        for slot_idx in range(places_per_course):
            required_type = slot_types[slot_idx] if slot_idx < len(slot_types) else ""

            # 해당 타입에 맞는 후보 필터링
            type_candidates = []
            fallback_candidates = []

            for c in scored_for_theme:
                pid = c.get("place", {}).get("id")
                if pid in used_place_ids:
                    continue

                inferred = c.get("inferred_type", "식당")

                if required_type and required_type in TYPE_MATCH_KEYWORDS:
                    # 타입 매칭 확인
                    match_kws = TYPE_MATCH_KEYWORDS[required_type]
                    place_name = c.get("place", {}).get("name", "").lower()
                    place_kw = c.get("place", {}).get("keywords", {})
                    menu_type = place_kw.get("menu_type", "") if isinstance(place_kw, dict) else ""

                    is_match = (
                        inferred == required_type or
                        any(mk in place_name for mk in match_kws) or
                        any(mk in str(menu_type) for mk in match_kws)
                    )

                    if is_match:
                        type_candidates.append(c)
                    else:
                        fallback_candidates.append(c)
                else:
                    # 타입 미지정 슬롯: 모든 후보 허용
                    type_candidates.append(c)

            # 타입 매칭 후보가 있으면 거기서, 없으면 fallback에서 선택
            pool = type_candidates[:CANDIDATE_POOL_SIZE] if type_candidates else fallback_candidates[:CANDIDATE_POOL_SIZE]

            if not pool:
                continue

            # [v7] 왔다갔다(backtracking) 감지 페널티
            # - 멀리 가는 것 자체는 OK (동명동→첨단 한 방향 이동)
            # - 다시 돌아오는 것만 페널티 (동명동→첨단→동명동)
            if len(selected_places) >= 2:
                last = selected_places[-1]
                scores = []
                for c in pool:
                    p = c.get("place", {})
                    p_lat, p_lng = p.get("lat", 0), p.get("lng", 0)
                    dist_to_last = haversine_km(last["lat"], last["lng"], p_lat, p_lng)
                    # 이전 장소(마지막 제외)로 되돌아가는지 체크
                    backtrack_penalty = 0
                    for earlier in selected_places[:-1]:
                        dist_to_earlier = haversine_km(earlier["lat"], earlier["lng"], p_lat, p_lng)
                        if dist_to_earlier < dist_to_last * 0.5 and dist_to_last > 3.0:
                            # 마지막 장소보다 이전 장소에 훨씬 가까움 = 되돌아감
                            backtrack_penalty = -4.0
                            break
                    adjusted = max(c["theme_score"] + backtrack_penalty, 0.1)
                    scores.append(adjusted)
            else:
                scores = [max(c["theme_score"], 0.1) for c in pool]

            total = sum(scores)
            weights = [s / total for s in scores]

            chosen = random.choices(pool, weights=weights, k=1)[0]
            place = chosen.get("place", {})
            place_id = place.get("id")

            if place_id:
                used_place_ids.add(place_id)

                base_reason = chosen.get("score_breakdown", {}).get("sentiment_summary", "")
                theme_context = {
                    "데이트": "연인과 함께하기 좋은 곳입니다.",
                    "맛집": "맛집 탐방에 빠질 수 없는 곳입니다.",
                    "카페": "커피 한 잔의 여유를 즐기기 좋습니다.",
                    "디저트": "달콤한 디저트를 즐기기에 완벽합니다.",
                    "뷰맛집": "탁 트인 전망과 함께 즐기기 좋습니다.",
                    "힐링": "조용히 힐링하기 좋은 공간입니다.",
                    "가성비": "가성비 좋게 즐길 수 있습니다.",
                }
                context_suffix = theme_context.get(theme, f"{theme}에 어울리는 곳입니다.")

                if base_reason and len(base_reason) >= 5:
                    # 부정적 감성이면 테마 문구를 붙이지 않음 (앞뒤 모순 방지)
                    negative_keywords = ["아쉽", "별로", "실망", "부족", "불친절", "비싸", "않"]
                    is_negative = any(kw in base_reason for kw in negative_keywords)
                    if is_negative:
                        reason = base_reason[:30]
                    else:
                        reason = f"{base_reason[:30]}. {context_suffix}"
                else:
                    reason = context_suffix

                # 타입은 survey 슬롯 타입 우선, 없으면 추론
                final_type = required_type if required_type else chosen.get("inferred_type", "식당")

                selected_places.append({
                    "id": f"p{slot_idx+1}",
                    "name": place.get("name", "알 수 없음"),
                    "type": final_type,
                    "lat": place.get("lat", 0),
                    "lng": place.get("lng", 0),
                    "reason": reason[:60]
                })

        # 예산 계산
        total_budget = 0
        price_map = {
            "PRICE_LEVEL_FREE": 0, "PRICE_LEVEL_INEXPENSIVE": 8000,
            "PRICE_LEVEL_MODERATE": 15000, "PRICE_LEVEL_EXPENSIVE": 30000,
            "PRICE_LEVEL_VERY_EXPENSIVE": 50000, "": 12000
        }
        for item in analyzed_results:
            p = item.get("place", {})
            if p.get("name") in [sp["name"] for sp in selected_places]:
                total_budget += price_map.get(p.get("price_level", ""), 12000)
        budget_str = f"약 {total_budget:,}원" if total_budget > 0 else "약 50,000원"

        course = {
            "course_id": theme_idx + 1,
            "course_name": f"{theme} 코스",
            "course_description": f"'{theme}' 테마에 맞춰 엄선된 {len(selected_places)}곳을 추천합니다.",
            "places": selected_places,
            "total_budget": budget_str
        }
        generated_courses.append(course)
        type_summary = " → ".join([sp["type"] for sp in selected_places])
        print(f"[Scoring v6] 📍 코스 {theme_idx+1} '{theme}' ({len(selected_places)}곳): {type_summary}")

    print(f"✅ [Scoring Node v6] 코스 생성 완료: {len(generated_courses)}개 코스 (Slot-based Matching)")
    
    return {
        "scored_results": analyzed_results,
        "generated_courses": generated_courses  # 직접 코스 반환!
    }


def _infer_place_type(place: dict) -> str:
    """장소 타입 추론"""
    name = place.get("name", "").lower()
    keywords = place.get("keywords", {})
    
    # 키워드에서 타입 추론
    menu_type = keywords.get("menu_type", "")
    if isinstance(menu_type, str):
        if "카페" in menu_type or "커피" in menu_type or "디저트" in menu_type:
            return "카페"
        if "베이커리" in menu_type or "빵" in menu_type:
            return "베이커리"
    
    # 이름에서 추론
    if "카페" in name or "커피" in name or "coffee" in name:
        return "카페"
    if "베이커리" in name or "빵" in name:
        return "베이커리"
    
    return "식당"

