"""
Response Node (General Agent)
enriched_results를 LLM으로 포맷팅하여 장소 리스트 JSON을 생성합니다.
기존 프론트엔드와 호환되는 recommended_courses 형식으로 출력합니다.
"""

import json
import time
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agent.config import config
from ..state import GeneralAgentState


def _format_places_for_prompt(enriched_results: list) -> str:
    """enriched_results를 프롬프트용 텍스트로 변환"""
    if not enriched_results:
        return "검색된 장소가 없습니다."

    parts = [f"## 후보 장소 목록 ({len(enriched_results)}개)"]

    for idx, item in enumerate(enriched_results, 1):
        place = item.get("place", {})
        temp_id = f"p{idx}"

        line = f"\n---\n### [ID: {temp_id}] {place.get('name', '알 수 없음')}"
        if place.get('lat') and place.get('lng'):
            line += f" (lat:{place['lat']}, lng:{place['lng']})"

        parts.append(line)
        parts.append(f"주소: {place.get('address', '정보 없음')}")
        parts.append(f"평점: {place.get('rating', 0)} ({place.get('total_reviews', 0)}개 리뷰)")

        reviews = place.get("reviews", [])
        if reviews:
            first_review = reviews[0].get("text", "")[:80]
            if first_review:
                parts.append(f"리뷰: {first_review}...")

    return "\n".join(parts)


async def response_node(state: GeneralAgentState) -> dict[str, Any]:
    """
    enriched_results를 기반으로 사용자 질문에 맞는 장소 추천 응답을 생성합니다.
    """
    messages = state.get("messages", [])
    last_message = messages[-1].content if messages and hasattr(messages[-1], 'content') else ""
    enriched_results = state.get("enriched_results", [])
    query_plan = state.get("query_plan") or {}
    user_instruction = query_plan.get("user_instruction", "")

    print(f"[General-Response] 응답 생성 시작: '{last_message}'")
    if user_instruction:
        print(f"[General-Response] 사용자 지시: '{user_instruction}'")

    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.3,
    )

    context_text = _format_places_for_prompt(enriched_results)

    instruction_block = ""
    if user_instruction:
        instruction_block = f"""
**[사용자 지시사항 - 반드시 따르세요]**
{user_instruction}
"""

    prompt = f"""당신은 광주광역시 장소 추천 AI 어시스턴트입니다.
사용자의 요청을 **정확히 그대로** 따라서 장소를 추천해주세요.

**[사용자 원본 요청]**
"{last_message}"
{instruction_block}
**[후보 장소 목록]**
{context_text}

**[핵심 원칙: 사용자 요청을 그대로 따르기]**
- 사용자가 "삼겹살집 5개"라고 하면 → 삼겹살/고기집만 정확히 5개. 카페나 다른 카테고리 섞지 말 것.
- 사용자가 "첫 번째는 스테이크집, 두 번째는 전시회관"이라고 하면 → 그 순서와 타입을 정확히 따를 것.
- 사용자가 개수를 지정하면 → 정확히 그 개수만 추천할 것.
- 사용자가 카테고리를 지정하면 → 해당 카테고리에 맞는 장소만 선별할 것.
- 후보 목록에 적합한 장소가 부족하면, 있는 것만이라도 최대한 맞춰서 추천할 것.

**[기타 규칙]**
- 각 장소에 왜 추천하는지 간단한 이유를 작성하세요.
- 제공된 [ID: pN] 목록에서 선택하고, lat/lng 좌표를 정확히 유지하세요.

**[출력 형식]**
반드시 아래 JSON 형식으로 출력하세요. (Markdown 코드블록 없이 JSON만 출력)

{{
    "answer": "사용자에게 보여줄 친절한 안내 메시지 (1~2문장)",
    "recommended_courses": [
        {{
            "course_id": 1,
            "course_name": "추천 장소",
            "course_description": "검색 결과 설명",
            "places": [
                {{
                    "id": "p1",
                    "name": "장소명",
                    "type": "식당/카페/관광지/전시관 등",
                    "lat": 35.0,
                    "lng": 126.0,
                    "reason": "추천 이유"
                }}
            ]
        }}
    ]
}}
"""

    try:
        t_start = time.time()
        response = await llm.ainvoke(prompt)
        print(f"[General-Response] LLM 응답: {time.time() - t_start:.2f}초")

        content = response.content.strip()

        # JSON 파싱
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:].strip()

        parsed = json.loads(content)
        final_json = json.dumps(parsed, ensure_ascii=False, indent=2)

        places_count = len(parsed.get('recommended_courses', [{}])[0].get('places', []))
        print(f"[General-Response] 완료: {places_count}개 장소 추천")

        return {"final_answer": final_json}

    except Exception as e:
        print(f"[General-Response] 오류: {e}")
        fallback = {
            "answer": "죄송합니다. 장소 정보를 정리하는 중에 문제가 발생했어요.",
            "recommended_courses": []
        }
        return {"final_answer": json.dumps(fallback, ensure_ascii=False)}
