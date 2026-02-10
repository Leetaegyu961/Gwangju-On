"""
Query Analyzer Node (General Agent)
사용자 질문을 분석하여 검색 쿼리를 생성합니다.
서베이 데이터, 개인화 컨텍스트 없이 순수하게 질문만 분석합니다.
"""

from typing import Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agent.config import config
from ..state import GeneralAgentState


class SearchPlan(BaseModel):
    """검색 쿼리 계획"""
    place_queries: list[str] = Field(
        description="Google Places API에 사용할 검색 쿼리 리스트. 사용자 질문에서 추출한 지역명 + 키워드 조합. 최대 5개."
    )
    result_count: int = Field(
        default=10,
        description="각 쿼리별 검색할 결과 개수 (기본 10, 최대 20)"
    )
    user_instruction: str = Field(
        default="",
        description="사용자의 원래 요청을 그대로 보존한 지시사항. 개수, 순서, 타입 지정 등을 포함. 예: '삼겹살집 5개', '첫 번째는 스테이크집, 두 번째는 전시회관'"
    )
    reasoning: str = Field(
        description="쿼리 생성 이유"
    )


async def query_analyzer(state: GeneralAgentState) -> dict[str, Any]:
    """
    사용자 질문을 분석하여 검색 쿼리를 생성합니다.
    서베이/개인화 없이 순수 질문 기반으로 동작합니다.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"query_plan": None}

    last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

    print(f"[General-Analyzer] 질문 분석 중: '{last_message}'")

    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0,
    )

    structured_llm = llm.with_structured_output(SearchPlan)

    prompt = f"""당신은 광주광역시 장소 검색 전문가입니다.
사용자 질문을 분석하여 Google Places API 검색 쿼리를 생성하세요.

사용자 질문: "{last_message}"

다음 규칙을 따르세요:

1. **place_queries**: 사용자의 요청을 충족시키기 위해 필요한 검색 쿼리를 모두 생성하세요.
   - 지역이 명시되어 있으면 그대로 사용 (예: "동명동 카페" → "광주 동명동 카페")
   - 지역이 없으면 "광주"를 기본으로 사용
   - **사용자가 여러 종류를 요청하면 각각에 맞는 쿼리를 별도로 생성하세요.**
     - 예: "첫 번째는 스테이크집, 두 번째는 전시회관" → ["광주 스테이크 레스토랑", "광주 전시회관 갤러리"]
     - 예: "삼겹살집 5개 추천" → ["광주 삼겹살 맛집", "광주 고기집", "광주 돼지고기 전문점"]
   - 최대 5개

2. **result_count**: 사용자가 특정 개수를 요청하면 충분한 후보를 확보할 수 있도록 설정
   - 기본값 10, 최대 20

3. **user_instruction**: 사용자의 원래 요청을 핵심만 보존하세요. response_node가 이 지시사항을 그대로 따릅니다.
   - 예: "삼겹살집 5개" → "삼겹살집만 정확히 5개 추천"
   - 예: "첫 번째는 스테이크집 두 번째는 전시회관 세 번째는 카페" → "1번: 스테이크집, 2번: 전시회관, 3번: 카페 순서로 각각 1개씩"
   - 예: "동명동 카페 리스트" → "동명동 카페를 가능한 많이 나열"

4. **reasoning**: 왜 이런 쿼리를 생성했는지 간단히 설명
"""

    try:
        plan = await structured_llm.ainvoke(prompt)

        if plan is None:
            print(f"[General-Analyzer] LLM이 None 반환. 기본값으로 진행.")
            return {
                "query_plan": {
                    "place_queries": [f"광주 {last_message}"],
                    "result_count": 10,
                    "reasoning": "LLM 응답 실패 - 사용자 질문을 그대로 검색어로 사용"
                }
            }

        print(f"[General-Analyzer] 검색 계획:")
        print(f"   - Queries: {plan.place_queries}")
        print(f"   - Count: {plan.result_count}")
        print(f"   - Reason: {plan.reasoning}")

        return {"query_plan": plan.model_dump()}

    except Exception as e:
        print(f"[General-Analyzer] 오류: {e}")
        return {
            "query_plan": {
                "place_queries": [f"광주 {last_message}"],
                "result_count": 10,
                "reasoning": f"오류로 기본 검색어 사용: {e}"
            }
        }
