"""
Scoring Node v4 (LLM 직접 점수화 - Batching 적용)
LLM이 4개 차원(맛/서비스/가성비/재방문)별로 직접 채점하는 방식입니다.
배치 처리(Batch Processing)를 통해 LLM 호출 수를 줄이고 속도를 개선했습니다.
"""

import os
import json
import asyncio
from typing import Any, List, Dict, Tuple
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
        
        places_text += f"""
---
### Place {idx + 1}: {place.get('name', 'Unknown')}
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

[
  {{
    "index": 1,
    "name": "음식점 이름",
    "taste": 1.5,
    "service": 2.0,
    "value": 1.0,
    "revisit": 1.0,
    "reason": "맛과 분위기가 좋고 재방문 의사가 높음"
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
    
    # 스코어링 시스템 (공공 데이터 점수용)
    base_dir = os.getcwd()
    data_dir = os.path.join(base_dir, "data")
    scoring_system = get_scoring_system(data_dir)
    
    # 배치 처리 준비
    batch_size = 5
    batches = [enriched_results[i:i + batch_size] for i in range(0, len(enriched_results), batch_size)]
    
    print(f"🤖 LLM 배치 채점 실행 중 ({len(batches)} 배치)...")
    
    # 비동기 병렬 실행
    tasks = [analyze_sentiment_batch(llm, batch) for batch in batches]
    batch_results = await asyncio.gather(*tasks)
    
    # 결과 평탄화 (Flatten)
    flat_sentiment_results = [item for sublist in batch_results for item in sublist]
    
    analyzed_results = []
    
    # 결과 합치기
    for item, (sentiment_score, sentiment_breakdown) in zip(enriched_results, flat_sentiment_results):
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
