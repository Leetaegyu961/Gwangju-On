"""
Course Generation Node
병렬로 실행되는 코스 생성 노드입니다.
각 노드는 할당된 테마(Theme)에 맞춰 하나의 코스를 생성합니다.
"""

from typing import Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import config
from ..state import AgentState


def _format_place_data(state: AgentState) -> str:
    """
    scored_results (또는 enriched_results)를 프롬프트 컨텍스트용 문자열로 변환합니다.
    """
    results_data = state.get("scored_results") or state.get("enriched_results")
    if not results_data:
        return "검색된 장소 데이터가 없습니다."

    has_scores = state.get("scored_results") is not None
    context_parts = []
    
    context_parts.append(f"## 🍽️ 후보 장소 목록 ({len(results_data)}개)")
    if has_scores:
        context_parts.append("*점수가 높은 순서대로 정렬되어 있습니다.*")
    
    # 상위 60개까지 컨텍스트에 포함 (다양성 확보를 위해 대폭 증가)
    for idx, item in enumerate(results_data[:60], 1):
        place = item.get('place', {})
        place_name = place.get('name', '알 수 없음')
        address = place.get('address', '주소 정보 없음')
        rating = place.get('rating', 0)
        total_reviews = place.get('total_reviews', 0)
        
        # 스코어 정보
        score = item.get('score', 0)
        score_breakdown = item.get('score_breakdown', {})
        
        # 임시 ID (p1, p2...)
        temp_id = f"p{idx}"
        
        title_line = f"\n---\n### [ID: {temp_id}] {place_name}"
        if has_scores and score > 0:
            title_line += f" ⭐️종합점수:{score}점"
            sentiment = score_breakdown.get('sentiment', 0)
            if sentiment > 0:
                title_line += f" (감성:{sentiment})"
        
        if place.get('lat') and place.get('lng'):
            title_line += f" (lat:{place['lat']}, lng:{place['lng']})"
            
        context_parts.append(title_line)
        context_parts.append(f"📍 주소: {address}")
        context_parts.append(f"⭐ 평점: {rating} ({total_reviews}개 리뷰)")
        
        # 스코어 세부내역
        if has_scores and score_breakdown:
            details = []
            if score_breakdown.get('exemplary', 0) > 0: details.append("모범음식점")
            if score_breakdown.get('gwangju_food', 0) > 0: details.append("광주맛집")
            summary = score_breakdown.get('sentiment_summary', '')
            if summary and summary != "분석 실패 - 기본값":
                details.append(f"평가:{summary}")
            if details:
                context_parts.append(f"🏅 특징: {', '.join(details)}")
        
        # 블로그 요약 (최대 1개만, 짧게)
        blogs = item.get('blogs', [])
        if blogs:
            first_blog = blogs[0]
            content = first_blog.get('full_content', '')[:100]
            if content:
                context_parts.append(f"📝 리뷰요약: {content}...")

    return "\n".join(context_parts)


async def _generate_single_course(state: AgentState, theme_idx: int) -> dict[str, Any]:
    """
    지정된 테마 인덱스에 해당하는 코스를 생성합니다.
    """
    themes = state.get("themes", [])
    # 테마가 부족할 경우 기본값 사용
    default_themes = ["맛집", "카페", "가성비"]
    
    if idx := theme_idx < len(themes):
        current_theme = themes[theme_idx]
    else:
        current_theme = default_themes[theme_idx] if theme_idx < len(default_themes) else "자유 테마"
        
    print(f"[Course Gen {theme_idx+1}] 테마 '{current_theme}' 코스 생성 시작...")
    
    # LLM 초기화
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.4, 
    )
    
    # 컨텍스트 데이터 준비
    context_text = _format_place_data(state)
    
    # 설문 데이터
    survey_data = state.get("survey_data", {})
    places_per_course = 4 # 기본값
    if isinstance(survey_data, dict):
        courses_list = survey_data.get("courses", [])
        if courses_list:
            places_per_course = len(courses_list)

    prompt = f"""당신은 여행 코스 플래너입니다.
제공된 장소 목록(Context Data)을 바탕으로, **"{current_theme}"** 테마에 딱 맞는 코스 하나를 생성하세요.

**[Context Data]**
{context_text}

**[요구사항]**
1. 테마: **{current_theme}** (이 테마에 부합하는 장소를 최우선으로 선택)
2. 장소 개수: 정확히 **{places_per_course}개**
3. 구성: 식사 -> 카페 -> 활동 등 자연스러운 동선으로 구성
4. **Diversity Strategy (중요)**:
   - 단순히 점수가 높은 장소를 고르지 마세요.
   - **반드시 "{current_theme}" 테마의 분위기와 특성에 맞는 장소를 선택하세요.**
   - 만약 상위권 장소가 테마와 맞지 않는다면 과감히 건너뛰고, 하위권이라도 테마에 맞는 장소를 선택하세요.
   - 다른 코스와 겹치지 않는 독창적인 장소를 우선적으로 고려하세요.
5. 장소 선택:
   - 제공된 [ID: pN] 목록에서 선택하세요.
   - lat, lng 좌표와 ID를 정확히 유지하세요.
6. **코스 제목(Course Title)**:
   - **반드시 6글자 이내로 짧게 작성하세요.** (예: "감성 가득 힐링", "광주 맛집 투어")
   - UI에서 잘리지 않도록 핵심만 담으세요.

**[출력 형식]**
반드시 아래 JSON 형식으로 출력하세요. (Markdown 코드블록 없이 JSON만 출력)

{{
    "course_id": {theme_idx + 1},
    "course_name": "6글자이내제목",
    "course_description": "이 코스는 {current_theme}를 주제로 한 여행 코스입니다...",
    "places": [
        {{
            "id": "p1",
            "name": "장소명",
            "type": "식당/카페",
            "lat": 35.0,
            "lng": 126.0,
            "reason": "선정 이유"
        }}
    ],
    "total_budget": "예상 1인 경비"
}}
"""

    try:
        response = await llm.ainvoke(prompt)
        raw_content = response.content
        if isinstance(raw_content, list):
             parts = []
             for item in raw_content:
                 if isinstance(item, str):
                     parts.append(item)
                 elif hasattr(item, 'text') and item.text:
                     parts.append(item.text)
                 else:
                     parts.append(str(item))
             content = "".join(parts)
        else:
             content = str(raw_content)
             
        content = content.strip()
        
        # JSON 파싱
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:].strip()
        
        try:
            course_data = json.loads(content)
        except json.JSONDecodeError:
            print(f"[Warn] [Course Gen {theme_idx+1}] JSON 파싱 실패, ast.literal_eval 시도")
            import ast
            try:
                course_data = ast.literal_eval(content)
            except Exception as e:
                print(f"[Error] [Course Gen {theme_idx+1}] ast 파싱 실패: {e}")
                # 최후의 수단: 단순히 에러 던지기 전에 내용을 한번 출력
                print(f"Content content: {content}")
                raise e
        
        # [Fix] 중첩된 JSON 구조 처리 (Recursive Parsing)
        # 예: {'type': 'text', 'text': '{...}'} 형태로 오는 경우
        if isinstance(course_data, dict) and "places" not in course_data and "text" in course_data:
            print(f"[Info] [Course Gen {theme_idx+1}] 중첩된 JSON 구조 감지, 재파싱 시도...")
            inner_text = course_data["text"]
            if isinstance(inner_text, str):
                inner_text = inner_text.strip()
                if inner_text.startswith("```"):
                    inner_text = inner_text.split("```")[1]
                    if inner_text.startswith("json"):
                        inner_text = inner_text[4:].strip()
                try:
                    course_data = json.loads(inner_text)
                    print(f"[Info] [Course Gen {theme_idx+1}] 재파싱 성공!")
                except json.JSONDecodeError:
                     import ast
                     try:
                        course_data = ast.literal_eval(inner_text)
                        print(f"[Info] [Course Gen {theme_idx+1}] 재파싱(ast) 성공!")
                     except:
                        pass # 재파싱 실패 시 원래 데이터 사용

        
        # ID 강제 주입 (병합 시 식별용)
        course_data["course_id"] = theme_idx + 1
        
        # 데이터 무결성 검사
        places_found = course_data.get("places", [])
        if not places_found:
            print(f"[Warn] [Course Gen {theme_idx+1}] 'places' 목록이 비어있습니다. (AI Output: {str(course_data)[:50]}...)")
        
        return {"generated_courses": [course_data]}
        
    except Exception as e:
        print(f"[Error] [Course Gen {theme_idx+1}] 생성 실패: {e}")
        # 실패 시 빈 리스트 (또는 에러 표시된 더미 데이터)
        return {"generated_courses": []}


async def generate_course_1(state: AgentState) -> dict[str, Any]:
    return await _generate_single_course(state, 0)

async def generate_course_2(state: AgentState) -> dict[str, Any]:
    return await _generate_single_course(state, 1)

async def generate_course_3(state: AgentState) -> dict[str, Any]:
    return await _generate_single_course(state, 2)
