"""
Query Planner Node
LLM을 사용하여 사용자 의도를 파악하고 최적화된 검색 쿼리 및 3가지 테마를 생성합니다.
"""

from typing import Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import config
from ..state import AgentState


class QueryPlan(BaseModel):
    """검색 쿼리 및 테마 계획"""
    themes: list[str] = Field(
        description="사용자 의도를 분석하여 도출한 3가지 추천 코스 테마 키워드. (예: ['힐링', '데이트', '맛집']). 반드시 지역명을 제외한 1~2단어의 핵심 명사만 추출할 것."
    )
    place_queries: list[str] = Field(
        default=[],
        description="Google Places API에 사용할 검색 쿼리 리스트. 3가지 테마를 모두 커버할 수 있도록 생성하되, 반드시 최대 3개로 제한하세요."
    )
    result_count: int = Field(
        default=20,
        description="각 쿼리별 검색할 결과 개수 (기본 20, 최대 20). 코스 3개를 만들려면 충분한 장소가 필요함."
    )
    reasoning: str = Field(
        description="테마 선정 및 쿼리 생성 이유"
    )


async def query_planner_node(state: AgentState) -> dict[str, Any]:
    """
    사용자 질문을 분석하여 3가지 테마와 최적화된 검색 쿼리를 생성합니다. (Async)

    Args:
        state: 현재 에이전트 상태

    Returns:
        업데이트된 상태 (query_plan, themes)
    """
    # 마지막 사용자 메시지 가져오기
    messages = state.get("messages", [])
    if not messages:
        return {"query_plan": None}

    last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

    print(f"[Planner] 쿼리 및 테마 계획 생성 중: '{last_message}'")

    # LLM 초기화 (Structured Output 사용)
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0,  # 일관된 결과를 위해 0
    )

    # Structured Output으로 쿼리 계획 생성
    structured_llm = llm.with_structured_output(QueryPlan)

    # 서베이 데이터 가져오기
    survey_data = state.get("survey_data", {})
    print(f"[Planner] Survey Data received: {survey_data}")  # 디버깅 로그 추가

    user_context = ""
    if survey_data:
        gender = survey_data.get("gender", "알 수 없음")
        age = survey_data.get("age", "알 수 없음")
        themes = ", ".join(survey_data.get("themes", []))
        companions = ", ".join(survey_data.get("companions", []))
        region = survey_data.get("region", "알 수 없음")
        user_context = f"""
[사용자 정보]
- 성별/나이: {gender}, {age}
- 여행 테마: {themes}
- 동행인: {companions}
- 선호 지역: {region}
"""

    # 개인화 컨텍스트 추가 (테이스팅 노트 + 선호도 + 이전 대화 요약)
    personalization = state.get("personalization_context", "")
    if personalization:
        user_context += f"\n[개인화 컨텍스트 (이전 여행 이력 기반)]\n{personalization}\n"
        print(f"[Planner] 개인화 컨텍스트 적용됨: {personalization[:80]}...")

    prompt = f"""당신은 사용자 질문을 분석하여 '3가지 추천 테마'와 '검색 쿼리'를 생성하는 전문가입니다.
{user_context}
사용자 질문: "{last_message}"

**중요: 사용자 질문에 특정 지역(예: 성수동, 부산 등)이 명시되어 있지 않다면, 반드시 [사용자 정보]의 '선호 지역'을 기준으로 검색 쿼리를 생성하세요.**

다음 규칙에 따라 계획을 수립하세요:

1. **themes** (3가지 추천 테마):
   - **매우 엄격한 규칙**: 테마 이름은 반드시 **2~4 글자 이내의 단어(명사)**여야 합니다.
   - **절대 금지 사항**:
     - 지역명 포함 금지 (예: "성수동", "광주" 등 절대 금지)
     - 수식어/형용사 금지 (예: "숨겨진", "감성적인", "최고의", "투어", "탐방" 등 금지)
     - 문장형 금지
   - **형식**: 핵심 컨셉 단어만 작성 (프론트엔드에서 자동으로 'OO 코스'라고 붙여서 보여줍니다.)
   - **예시**:
     - (Good - 채택): "힐링", "맛집", "데이트", "산책", "포토존", "가성비", "디저트"
     - (Bad - 절대 금지): "성수동 맛집 투어", "숨겨진 힐링 명소", "감성 가득한 카페", "친구와 함께하는 여행", "맛집 코스"

2. **place_queries** (Google Places 검색어 리스트):
  - 위에서 선정한 **3가지 테마를 모두 포괄할 수 있는 검색어**를 생성하세요.
  - **각 테마별로 특화된 검색어를 포함하여 결과의 다양성을 확보하세요.**
    - 예: 테마가 ["힐링", "먹방", "포토존"]이라면 -> ["광주 동명동 조용한 카페", "광주 동명동 맛집", "광주 동명동 사진 찍기 좋은 곳"]
  - 맛집, 식당, 카페 등 장소를 찾는 질문이면 생성
  - **사용자가 식당과 카페를 둘 다 원하는 경우(코스), 각각의 검색어를 리스트에 포함하세요.**
  - 장소 이름을 명확히 포함 (예: "광주 동명동 맛집", "광주 동명동 한식", "광주 동명동 카페")
  - 맛집 관련이 아니면 빈 리스트 []

3. **result_count** (쿼리당 결과 개수):
   - 각 쿼리별로 몇 개씩 검색할지 설정
   - 기본값 10, 최대 20 (3개의 서로 다른 코스를 만들려면 충분한 장소가 필요함)

4. **reasoning**:
   - 왜 이런 테마와 쿼리를 생성했는지 간단히 설명

예시:
- "광주 동명동에서 데이트할거야"
  → themes: ["데이트", "포토존", "이색"]  <-- (Good: 지역명 없음, 핵심 단어만)
  → place_queries: ["광주 동명동 분위기 좋은 맛집", "광주 동명동 사진 찍기 좋은 카페", "광주 동명동 이색 데이트"], result_count: 10
"""

    try:
        # Async invoke
        query_plan = await structured_llm.ainvoke(prompt)

        # LLM이 None을 반환한 경우 서베이 기반 기본값으로 진행
        if query_plan is None:
            print(f"[Planner] LLM이 None을 반환함. 서베이 기반 기본 테마로 진행합니다.")
            fallback_region = survey_data.get("region", "광주") if survey_data else "광주"
            return {
                "query_plan": {
                    "themes": ["맛집", "카페", "힐링"],
                    "place_queries": [f"{fallback_region} 맛집", f"{fallback_region} 카페", f"{fallback_region} 관광명소"],
                    "result_count": 20,
                    "reasoning": "LLM 응답 실패로 서베이 기반 기본 테마 사용"
                },
                "themes": ["맛집", "카페", "힐링"]
            }

        print(f"[Planner] 쿼리 계획 (Async):")
        print(f"   - Themes: {query_plan.themes}")
        print(f"   - Place Queries: {query_plan.place_queries}")
        print(f"   - 개수(쿼리당): {query_plan.result_count}개")
        print(f"   - 이유: {query_plan.reasoning}")

        return {
            "query_plan": query_plan.model_dump(),
            "themes": query_plan.themes  # state에 themes 저장
        }

    except Exception as e:
        print(f"[Error] 쿼리 계획 생성 오류: {e}")
        # 실패 시 서베이 기반 기본 쿼리로 진행
        fallback_region = survey_data.get("region", "광주") if survey_data else "광주"
        return {
            "query_plan": {
                "themes": ["맛집", "카페", "힐링"],
                "place_queries": [f"{fallback_region} 맛집", f"{fallback_region} 카페", f"{fallback_region} 관광명소"],
                "result_count": 20,
                "reasoning": f"LLM 오류로 기본 테마 사용 (지역: {fallback_region})"
            },
            "themes": ["맛집", "카페", "힐링"]
        }
