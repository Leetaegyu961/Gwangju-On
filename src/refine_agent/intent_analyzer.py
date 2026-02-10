"""
Intent Analyzer
사용자의 코스 수정 요청을 Gemini Structured Output으로 분석합니다.
"""

import os
import json
from pydantic import BaseModel, Field
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")


class RefinementIntent(BaseModel):
    """사용자의 코스 수정 의도"""
    action: str = Field(description="수정 유형: swap(교체), remove(제거), add(추가), shift_location(위치이동), change_theme(분위기변경), change_type(타입변경)")
    course_idx: int = Field(default=0, description="대상 코스 인덱스 (0-based)")
    slot_idx: int = Field(default=-1, description="대상 장소 인덱스 (0-based, -1이면 AI가 판단)")
    criteria: str = Field(default="", description="원하는 조건 키워드")
    direction: Optional[str] = Field(default=None, description="위치 방향: north/south/east/west")
    new_type: Optional[str] = Field(default=None, description="변경할 장소 타입: 식당/카페/숙박/놀거리")
    reasoning: str = Field(default="", description="분석 이유")


async def analyze_refinement_intent(
    message: str,
    current_courses: list,
    course_index: int
) -> RefinementIntent:
    """Gemini Structured Output으로 사용자의 수정 의도를 분석합니다."""

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
    )
    structured_llm = llm.with_structured_output(RefinementIntent)

    course_summary = ""
    if 0 <= course_index < len(current_courses):
        course = current_courses[course_index]
        places = course.get("places", [])
        course_summary = f"코스명: {course.get('course_name', '?')}\n"
        for i, p in enumerate(places):
            course_summary += f"  {i+1}번: {p.get('name', '?')} ({p.get('type', '?')})\n"

    prompt = f"""사용자가 여행 코스를 수정하고 싶어합니다. 요청을 분석하세요.

현재 코스 (인덱스 {course_index}):
{course_summary}

사용자 요청: "{message}"

규칙:
- "바꿔줘", "교체", "다른 곳" → action: swap
- "빼줘", "제거", "삭제" → action: remove
- "추가", "넣어줘", "하나 더" → action: add
- "오른쪽/왼쪽/위/아래/동쪽/북쪽" → action: shift_location, direction 설정
- "조용한/분위기/가성비/감성" 등 분위기 → action: change_theme
- "카페로/식당으로" 타입 변경 → action: change_type
- 장소 번호("1번째", "두번째")가 언급되면 slot_idx 설정 (0-based)
- course_idx는 기본 {course_index}
"""

    try:
        intent = await structured_llm.ainvoke(prompt)
        if intent.course_idx == -1:
            intent.course_idx = course_index
        print(f"🧠 [RefineAgent] Intent: {intent.action}, slot={intent.slot_idx}, criteria='{intent.criteria}'")
        return intent
    except Exception as e:
        print(f"⚠️ [RefineAgent] Intent analysis failed: {e}")
        return RefinementIntent(action="swap", course_idx=course_index, slot_idx=0, criteria=message)
