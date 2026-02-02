"""
LLM Node (개선 버전)
Place API와 Naver Search 데이터를 SystemMessage로 주입하여 LLM에 전달합니다.
"""

from typing import Any
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import config
from ..state import AgentState
from ..tools import search_tool


def _create_context_message(state: AgentState) -> SystemMessage | None:
    """
    enriched_results (블로그 + Places 리뷰 통합 데이터)를 SystemMessage로 변환합니다.
    (동기 함수 유지 - LLM 호출 없음)
    """
    # 컨텍스트 예산 설정
    MAX_CONTEXT_CHARS = 50000  # 컨텍스트 예산 증액
    MAX_REVIEW_CHARS = 800
    MAX_BLOG_CHARS = 5000
    
    context_parts = []
    total_chars = 0
    
    # scored_results 우선 사용 (없으면 enriched_results 사용)
    results_data = state.get("scored_results") or state.get("enriched_results")
    has_scores = state.get("scored_results") is not None
    
    if results_data:
        context_parts.append(f"## 🍽️ 맛집 검색 결과 ({len(results_data)}개)")
        if has_scores:
            context_parts.append("*점수가 높은 순서대로 정렬되어 있습니다.*")
        
        for idx, item in enumerate(results_data, 1):
            item_section = []
            
            # 1. 기본 가게 정보
            place = item.get('place', {})
            place_name = place.get('name', '알 수 없음')
            address = place.get('address', '주소 정보 없음')
            rating = place.get('rating', 0)
            total_reviews = place.get('total_reviews', 0)
            price_level = place.get('price_level', '')
            
            # 스코어 정보 (있는 경우)
            score = item.get('score', 0)
            score_breakdown = item.get('score_breakdown', {})
            
            # 가격대 변환
            price_str = ""
            if price_level == "PRICE_LEVEL_INEXPENSIVE": price_str = " (가격: ₩ - 저렴함)"
            elif price_level == "PRICE_LEVEL_MODERATE": price_str = " (가격: ₩₩ - 보통)"
            elif price_level == "PRICE_LEVEL_EXPENSIVE": price_str = " (가격: ₩₩₩ - 비쌈)"
            elif price_level == "PRICE_LEVEL_VERY_EXPENSIVE": price_str = " (가격: ₩₩₩₩ - 매우 비쌈)"
            
            # 임시 ID 생성 (p1, p2...)
            temp_id = f"p{idx}"
            
            title_line = f"\n---\n### [ID: {temp_id}] {place_name}{price_str}"
            
            if has_scores and score > 0:
                title_line += f" ⭐️ 종합점수: {score}점"
                # 감성 점수 표시
                sentiment = score_breakdown.get('sentiment', 0)
                if sentiment > 0:
                    title_line += f" (감성: {sentiment}점)"
            
            if place.get('lat') and place.get('lng'):
                title_line += f" (lat: {place['lat']}, lng: {place['lng']})"
            item_section.append(title_line)

            item_section.append(f"📍 주소: {address}")
            item_section.append(f"⭐ 평점: {rating} ({total_reviews}개 리뷰)")
            
            # 스코어 세부내역 추가 (있는 경우)
            if has_scores and score_breakdown:
                score_details = []
                if score_breakdown.get('exemplary', 0) > 0:
                    score_details.append("모범음식점 인증")
                if score_breakdown.get('gwangju_food', 0) > 0:
                    score_details.append("광주 맛집 선정")
                if score_breakdown.get('blogs', 0) > 0:
                    blog_count = len(item.get('blogs', []))
                    score_details.append(f"블로그 {blog_count}개 언급")
                
                # 감성 분석 요약 추가
                sentiment_summary = score_breakdown.get('sentiment_summary', '')
                if sentiment_summary and sentiment_summary != "분석 실패 - 기본값":
                    score_details.append(f"리뷰 평가: {sentiment_summary}")
                
                if score_details:
                    item_section.append(f"🏅 인증: {', '.join(score_details)}")
            
            # 2. Google Places 리뷰 (최대 3개)
            reviews = place.get('reviews', [])
            if reviews:
                item_section.append(f"\n**📣 Google 사용자 리뷰**:")
                for r in reviews[:3]: # 3개만 샘플링
                    review_text = r.get('text', '')[:MAX_REVIEW_CHARS]
                    review_text = review_text.replace('\n', ' ')
                    rating_star = "⭐" * int(r.get('rating', 0))
                    item_section.append(f"- {rating_star} {review_text}")
            
            # 3. Naver 블로그/RSS 후기 (최대 3개)
            blogs = item.get('blogs', [])
            if blogs:
                item_section.append(f"\n**📝 Naver 블로그 상세 후기 ({len(blogs)}개 발견)**:")
                
                for blog in blogs[:3]: # 블로그도 3개만 샘플링
                    title = blog.get('title', '제목 없음')
                    blogger = blog.get('bloggername', '익명')
                    post_date = blog.get('postdate', '')
                    content = blog.get('full_content', '')
                    
                    if len(content) > MAX_BLOG_CHARS:
                        content = content[:MAX_BLOG_CHARS] + "...(중략)"
                    
                    item_section.append(f"\n[블로그: {title}] - {blogger} ({post_date})")
                    item_section.append(f"내용 요약: {content}\n")
            else:
                item_section.append("\n⚠️ 매칭된 블로그 후기가 없습니다.")
            
            item_text = "\n".join(item_section)
            
            # 제한 없이 모두 포함 (사용자 요청)
            context_parts.extend(item_section)
            total_chars += len(item_text)
            
            # if total_chars + len(item_text) < MAX_CONTEXT_CHARS:
            #     context_parts.extend(item_section)
            #     total_chars += len(item_text)
            # else:
            #     print(f"⚠️ 컨텍스트 예산 초과 - {idx-1}개 가게까지만 포함됨")
            #     break
        
        context_parts.append("")
    
    # 컨텍스트가 있으면 SystemMessage 생성
    if context_parts:
        context_text = "\n".join(context_parts)
        
        print(f"📊 프롬프트 컨텍스트 크기: {len(context_text):,}자")
        
        # 설문에서 지정한 코스당 장소 개수 추출 (기본값: 4)
        survey_data = state.get("survey_data", {})
        if isinstance(survey_data, dict):
            courses_list = survey_data.get("courses", [])
            places_per_course = len(courses_list) if courses_list else 4
        else:
            places_per_course = 4
        
        print(f"📍 코스당 장소 개수: {places_per_course}개")
        
        system_prompt = f"""당신은 맛집 정보를 분석하여 사용자에게 추천해주는 전문 AI 에이전트입니다.

아래 제공된 **컨텍스트 데이터(Context Data)**는 Google Places API와 Naver Blog RSS를 통해 실시간으로 수집된 것입니다.
각 장소에는 **[ID: p1]**과 같은 고유 ID가 부여되어 있습니다.
이 데이터를 바탕으로 **3개의 서로 다른 추천 코스**를 생성하세요.

**[Context Data]**
{context_text}

**[User Info]**
{state.get("survey_data", "정보 없음")}

**[답변 작성 가이드]**
반드시 아래 **JSON 형식**으로 **3개의 서로 다른 코스**를 추천하세요. 마크다운(` ```json `)이나 다른 말은 붙이지 마세요.

**🚨 코스 구성 시 핵심 규칙 (반드시 준수):**
1. **각 코스의 식당/카페는 중복되면 안 됩니다!** 코스 1에 포함된 식당은 코스 2, 3에 절대 포함하지 마세요.
2. 컨텍스트에 있는 모든 장소를 3개 코스에 고르게 분배하세요.
3. **각 코스는 정확히 {places_per_course}개 장소로 구성하세요.** (사용자가 설문에서 지정한 개수입니다)

**코스 구성 시 중요 사항:**
- **종합점수가 높은 맛집을 우선적으로 고려**하세요. 점수가 높다는 것은:
  - 모범음식점 인증 또는 광주 맛집으로 선정됨
  - 다수의 블로그에서 언급됨
  - Google 평점과 리뷰 수가 많음

각 코스는 다음 테마 중 하나를 선택하여 차별화하세요:
1. 맛집 탐방 코스: 평점과 점수가 가장 높은 맛집 위주로 구성
2. 효율 이동 코스: 거리가 가까운 장소들로 동선을 최적화
3. 인스타 핫플 코스: SNS에서 인기있는 분위기 좋은 장소 위주

{{
    "answer": "3개의 추천 코스를 생성했습니다. 원하시는 코스를 선택해주세요.",
    "recommended_courses": [
        {{
            "course_id": 1,
            "course_name": "맛집 탐방 코스",
            "course_description": "코스에 대한 한 줄 설명",
            "places": [
                {{
                    "id": "p1",
                    "name": "장소 이름",
                    "type": "식당/카페/명소",
                    "lat": 35.1234,
                    "lng": 126.1234,
                    "reason": "장소 추천 이유"
                }}
            ],
            "total_budget": "예상 총액"
        }},
        {{
            "course_id": 2,
            "course_name": "효율 이동 코스",
            "course_description": "코스에 대한 한 줄 설명",
            "places": [ ... ],
            "total_budget": "예상 총액"
        }},
        {{
            "course_id": 3,
            "course_name": "인스타 핫플 코스",
            "course_description": "코스에 대한 한 줄 설명",
            "places": [ ... ],
            "total_budget": "예상 총액"
        }}
    ]
}}

주의사항:
1. 각 코스의 `places` 배열에는 추천하는 장소들을 순서대로 넣어주세요. **Context에 있는 lat, lng, id 값을 그대로 사용하세요.**
2. **🚨 3개 코스의 식당/카페는 절대 겹치면 안 됩니다!** 코스별로 완전히 다른 장소를 배치하세요.
3. `answer` 필드는 간결하게 작성하세요.
4. 형식을 철저히 지키세요. 반드시 3개의 코스를 모두 포함하세요.
"""
        
        return SystemMessage(content=system_prompt)
    
    return None



async def llm_node(state: AgentState) -> dict[str, Any]:
    """
    LLM을 호출하여 응답을 생성하는 노드입니다. (Async)
    """
    # LLM 초기화
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.4, 
    )
    
    # 도구 바인딩
    tools = [search_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    # 기존 메시지 가져오기
    messages = list(state["messages"])
    
    # 컨텍스트 메시지 생성 및 추가
    context_message = _create_context_message(state)
    
    if context_message:
        if messages and isinstance(messages[0], SystemMessage):
            messages[0] = context_message
        else:
            messages.insert(0, context_message)
        
        print("📤 LLM에 컨텍스트 주입 완료")
    
    # Async LLM 호출
    response = await llm_with_tools.ainvoke(messages)
    
    # 도구 호출이 필요한지 확인
    if response.tool_calls:
        return {
            "messages": [response],
            "current_step": "tool_calling",
        }
    
    # 최종 응답
    return {
        "messages": [response],
        "current_step": "responding",
        "final_answer": response.content,
    }
