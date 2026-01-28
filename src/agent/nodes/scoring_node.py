"""
Scoring Node v4 (LLM 직접 점수화)
LLM이 4개 차원(맛/서비스/가성비/재방문)별로 직접 채점하는 방식입니다.
"""

import os
import json
import asyncio
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from ..state import AgentState
from ..scoring_system import get_scoring_system
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


async def analyze_sentiment_v4(llm: ChatGoogleGenerativeAI, enriched_item: dict) -> tuple[float, dict]:
    """
    v4: LLM이 4개 차원별로 직접 채점
    
    Args:
        llm: LLM 인스턴스
        enriched_item: {"place": {...}, "blogs": [...]}
        
    Returns:
        (total_score, breakdown)
        - total_score: 0~6점
        - breakdown: {"taste": 2.0, "service": 1.5, "value": 1.0, "revisit": 1.0, "reason": "..."}
    """
    place = enriched_item.get("place", {})
    blogs = enriched_item.get("blogs", [])
    reviews = place.get("reviews", [])
    
    # 리뷰 텍스트 수집
    blog_texts = []
    for blog in blogs[:3]:
        content = blog.get("full_content", "")[:500]
        if content:
            blog_texts.append(content)
    
    review_texts = []
    for review in reviews[:5]:
        text = review.get("text", "")[:200]
        if text:
            review_texts.append(f"⭐{review.get('rating', 0)}점: {text}")
    
    blog_summary = "\n".join(blog_texts) if blog_texts else "블로그 리뷰 없음"
    review_summary = "\n".join(review_texts) if review_texts else "Google 리뷰 없음"
    
    prompt = f"""당신은 음식점 리뷰 전문 평가사입니다.
아래 리뷰들을 읽고 4가지 차원에서 점수를 매기세요.

{SCORING_RUBRIC}

---

## 평가 대상: {place.get('name', 'Unknown')}

### Google Places 리뷰
{review_summary}

### Naver 블로그 리뷰
{blog_summary}

---

## 출력 형식 (JSON만, 다른 말 X)
{{"taste": 1.5, "service": 2.0, "value": 1.0, "revisit": 1.0, "reason": "맛과 분위기가 좋고 재방문 의사가 높음"}}
"""
    
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # JSON 파싱
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:].strip()
        
        result = json.loads(content)
        
        # 점수 추출 및 범위 제한
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
        
        return round(total_score, 2), breakdown
        
    except Exception as e:
        print(f"⚠️ [v4 Scoring] LLM 분석 실패: {e}")
        # 실패 시 기본값 반환 (중립)
        default_breakdown = {
            "taste": 1.0,
            "service": 1.0,
            "value": 0.5,
            "revisit": 0.5,
            "total": 3.0,
            "reason": "분석 실패 - 기본값 사용"
        }
        return 3.0, default_breakdown


async def scoring_node(state: AgentState) -> dict[str, Any]:
    """
    v4: enriched_results를 입력으로 받아 LLM 직접 채점을 수행하고 scored_results를 반환합니다.
    
    Args:
        state: 현재 에이전트 상태 (enriched_results 포함)
        
    Returns:
        업데이트된 상태 {"scored_results": [...]}
    """
    enriched_results = state.get("enriched_results")
    
    if not enriched_results:
        print("⚠️ [Scoring Node] enriched_results가 없습니다.")
        return {"scored_results": None}
    
    print(f"\n📊 [Scoring Node v4] LLM 직접 채점 시작: {len(enriched_results)}개 음식점")
    
    # LLM 초기화
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.3,  # 약간의 일관성 향상
    )
    
    # 스코어링 시스템 (공공 데이터 점수용)
    base_dir = os.getcwd()
    data_dir = os.path.join(base_dir, "data")
    scoring_system = get_scoring_system(data_dir)
    
    # 비동기 병렬 실행
    print(f"🤖 LLM 직접 채점 비동기 실행 중 ({len(enriched_results)}개)...")
    
    tasks = [analyze_sentiment_v4(llm, item) for item in enriched_results]
    sentiment_results = await asyncio.gather(*tasks)
    
    analyzed_results = []
    
    # 결과 합치기
    for item, (sentiment_score, sentiment_breakdown) in zip(enriched_results, sentiment_results):
        place = item.get("place", {})
        
        # 기본 점수 계산 (공공 데이터 + Google 평점)
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
    
    return {"scored_results": analyzed_results}
