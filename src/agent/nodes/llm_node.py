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
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        컨텍스트가 포함된 SystemMessage 또는 None
    """
    # 컨텍스트 예산 설정
    MAX_CONTEXT_CHARS = 40000  # 컨텍스트 예산 증액
    MAX_REVIEW_CHARS = 500
    MAX_BLOG_CHARS = 3000
    
    context_parts = []
    total_chars = 0
    
    # enriched_results 데이터 처리 (블로그 + 리뷰 통합)
    enriched_results = state.get("enriched_results")
    
    if enriched_results:
        context_parts.append(f"## 🍽️ 맛집 검색 결과 ({len(enriched_results)}개)")
        
        for idx, item in enumerate(enriched_results, 1):
            item_section = []
            
            # 1. 기본 가게 정보
            place = item.get('place', {})
            place_name = place.get('name', '알 수 없음')
            address = place.get('address', '주소 정보 없음')
            rating = place.get('rating', 0)
            total_reviews = place.get('total_reviews', 0)
            price_level = place.get('price_level', '')
            
            # 가격대 변환
            price_str = ""
            if price_level == "PRICE_LEVEL_INEXPENSIVE": price_str = " (가격: ₩ - 저렴함)"
            elif price_level == "PRICE_LEVEL_MODERATE": price_str = " (가격: ₩₩ - 보통)"
            elif price_level == "PRICE_LEVEL_EXPENSIVE": price_str = " (가격: ₩₩₩ - 비쌈)"
            elif price_level == "PRICE_LEVEL_VERY_EXPENSIVE": price_str = " (가격: ₩₩₩₩ - 매우 비쌈)"
            
            # 임시 ID 생성 (p1, p2...)
            temp_id = f"p{idx}"
            
            title_line = f"\n---\n### [ID: {temp_id}] {place_name}{price_str}"
            # 원래 Google Place ID는 내부적으로만 가지고 있거나 필요시 병기
            
            if place.get('lat') and place.get('lng'):
                title_line += f" (lat: {place['lat']}, lng: {place['lng']})"
            item_section.append(title_line)

            item_section.append(f"📍 주소: {address}")
            item_section.append(f"⭐ 평점: {rating} ({total_reviews}개 리뷰)")
            
            # 2. Google Places 리뷰 (최대 3개)
            reviews = place.get('reviews', [])
            if reviews:
                item_section.append(f"\n**📣 Google 사용자 리뷰**:")
                for r in reviews[:3]: # 3개만 샘플링
                    review_text = r.get('text', '')[:MAX_REVIEW_CHARS]
                    # 줄바꿈 제거하여 간결하게
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
                    
                    # 본문이 너무 길면 자름
                    if len(content) > MAX_BLOG_CHARS:
                        content = content[:MAX_BLOG_CHARS] + "...(중략)"
                    
                    item_section.append(f"\n[블로그: {title}] - {blogger} ({post_date})")
                    item_section.append(f"내용 요약: {content}\n")
            else:
                item_section.append("\n⚠️ 매칭된 블로그 후기가 없습니다.")
            
            # 섹션 텍스트 합치기
            item_text = "\n".join(item_section)
            
            # 예산 체크
            if total_chars + len(item_text) < MAX_CONTEXT_CHARS:
                context_parts.extend(item_section)
                total_chars += len(item_text)
            else:
                print(f"⚠️ 컨텍스트 예산 초과 - {idx-1}개 가게까지만 포함됨")
                break
        
        context_parts.append("")
    
    # 컨텍스트가 있으면 SystemMessage 생성
    if context_parts:
        context_text = "\n".join(context_parts)
        
        print(f"📊 프롬프트 컨텍스트 크기: {len(context_text):,}자")
        
        system_prompt = f"""당신은 맛집 정보를 분석하여 사용자에게 추천해주는 전문 AI 에이전트입니다.

아래 제공된 **컨텍스트 데이터(Context Data)**는 Google Places API와 Naver Blog RSS를 통해 실시간으로 수집된 것입니다.
각 장소에는 **[ID: p1]**과 같은 고유 ID가 부여되어 있습니다.
이 데이터를 바탕으로 사용자의 질문에 답변하세요.

**[Context Data]**
{context_text}

**[User Info]**
{state.get("survey_data", "정보 없음")}

**[답변 작성 가이드]**
반드시 아래 **JSON 형식**으로만 답변하세요. 마크다운(` ```json `)이나 다른 말은 붙이지 마세요.

{{
    "answer": "사용자에게 보여줄 친절한 텍스트 답변 (여기에 줄바꿈은 \\n 사용)",
    "courses": [
        {{
            "id": "p1",   // Context에 있는 [ID]를 그대로 쓰세요 (필수, 이것으로 사진 매핑함)
            "name": "장소 이름",
            "type": "식당/카페/명소",
            "lat": 35.1234,  // Context의 lat
            "lng": 126.1234, // Context의 lng
            "reason": "장소 추천 이유"
        }},
        ... (최대 3~4개)
    ],
    "total_budget": "예상 총액 (문자열)"
}}

주의사항:
3. `courses` 배열에는 추천하는 장소들을 순서대로 넣어주세요. **Context에 있는 lat, lng, id 값을 그대로 사용하세요.**
4. `answer` 필드는 최대한 간결하게 작성하세요. 사용자는 텍스트보다 지도를 보고 싶어합니다. "요청하신 코스를 생성했습니다." 정도면 충분합니다.
5. 형식을 철저히 지키세요.
"""
        
        return SystemMessage(content=system_prompt)
    
    return None



def llm_node(state: AgentState) -> dict[str, Any]:
    """
    LLM을 호출하여 응답을 생성하는 노드입니다.
    Place API와 Naver Search 데이터를 컨텍스트로 주입합니다.
    """
    # LLM 초기화 (json_mode를 지원하는 모델이면 좋지만, 여기선 프롬프트로 강제)
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.4, # JSON 포맷 정확도를 위해 조금 낮춤
    )
    
    # 도구 바인딩
    tools = [search_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    # 기존 메시지 가져오기
    messages = list(state["messages"])
    
    # 컨텍스트 메시지 생성 및 추가
    context_message = _create_context_message(state)
    
    if context_message:
        # SystemMessage를 메시지 리스트 맨 앞에 삽입
        # (이미 SystemMessage가 있으면 교체)
        if messages and isinstance(messages[0], SystemMessage):
            messages[0] = context_message
        else:
            messages.insert(0, context_message)
        
        print("📤 LLM에 컨텍스트 주입 완료")
    
    # LLM 호출
    response = llm_with_tools.invoke(messages)
    
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
