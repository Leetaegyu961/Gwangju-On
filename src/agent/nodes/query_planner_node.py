"""
Query Planner Node
LLM을 사용하여 사용자 의도를 파악하고 최적화된 검색 쿼리를 생성합니다.
"""

from typing import Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import config
from ..state import AgentState


class QueryPlan(BaseModel):
    """검색 쿼리 계획"""
    place_queries: list[str] = Field(
        default=[],
        description="Google Places API에 사용할 검색 쿼리 리스트. (예: ['광주 동명동 맛집', '광주 동명동 카페'])"
    )
    result_count: int = Field(
        default=3,
        description="각 쿼리별 검색할 결과 개수 (기본 3, 최대 5)"
    )
    reasoning: str = Field(
        description="쿼리를 이렇게 생성한 이유"
    )


async def query_planner_node(state: AgentState) -> dict[str, Any]:
    """
    사용자 질문을 분석하여 최적화된 검색 쿼리를 생성합니다. (Async)
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        업데이트된 상태 (query_plan)
    """
    # 마지막 사용자 메시지 가져오기
    messages = state.get("messages", [])
    if not messages:
        return {"query_plan": None}
    
    last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
    
    print(f"🧠 쿼리 계획 생성 중: '{last_message}'")
    
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
    user_context = ""
    if survey_data:
        gender = survey_data.get("gender", "알 수 없음")
        age = survey_data.get("age", "알 수 없음")
        themes = ", ".join(survey_data.get("themes", []))
        companions = ", ".join(survey_data.get("companions", []))
        user_context = f"""
[사용자 정보]
- 성별/나이: {gender}, {age}
- 여행 테마: {themes}
- 동행인: {companions}
"""

    prompt = f"""당신은 사용자 질문을 분석하여 검색 쿼리를 생성하는 전문가입니다.
{user_context}
사용자 질문: "{last_message}"

다음 규칙에 따라 쿼리를 생성하세요:

1. **place_queries** (Google Places 검색어 리스트):
   - 맛집, 식당, 카페 등 장소를 찾는 질문이면 생성
   - **사용자가 식당과 카페를 둘 다 원하는 경우(코스), 각각의 검색어를 리스트에 포함하세요.**
   - 예: "동명동 맛집 추천해줘" -> ["광주 동명동 맛집"]
   - 예: "식당 갔다가 카페 가는 코스 알려줘" -> ["광주 동명동 식당", "광주 동명동 카페"]
   - 장소 이름을 명확히 포함
   - 맛집 관련이 아니면 빈 리스트 []

2. **result_count** (쿼리당 결과 개수):
   - 각 쿼리별로 몇 개씩 검색할지 설정
   - 기본값 3, 최대 5

3. **reasoning**:
   - 왜 이런 쿼리를 생성했는지 간단히 설명

예시:
- "광주 카레 맛집 3개만 추천해줘 동명동!" 
  → place_queries: ["광주 동명동 카레"], result_count: 3
  
- "서울 강남 일식 먹고 카페 갈래"
  → place_queries: ["서울 강남 일식", "서울 강남 카페"], result_count: 3
"""
    
    try:
        # Async invoke
        query_plan = await structured_llm.ainvoke(prompt)
        
        print(f"📋 쿼리 계획 (Async):")
        print(f"   - Place Queries: {query_plan.place_queries}")
        print(f"   - 개수(쿼리당): {query_plan.result_count}개")
        print(f"   - 이유: {query_plan.reasoning}")
        
        return {"query_plan": query_plan.model_dump()}
        
    except Exception as e:
        print(f"⚠️ 쿼리 계획 생성 오류: {e}")
        return {"query_plan": None}
