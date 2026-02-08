"""
Mini Agent with LangChain Tool Calling
LangChain AgentExecutor + Google Places API Tool
"""

import asyncio
import json
from typing import Dict, Any, Optional, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langsmith import traceable

from .config import config
from .place_search import search_places


# Google Places 검색 도구 정의
def _search_places_sync(query: str, max_results: int = 5) -> str:
    """
    Google Places API로 장소를 검색합니다.
    
    Args:
        query: 검색 쿼리 (예: "광주 동명동 카페")
        max_results: 최대 검색 결과 수 (기본값: 5)
    
    Returns:
        검색된 장소 정보 (JSON 문자열)
    """
    # 동기 래퍼
    places = asyncio.get_event_loop().run_until_complete(search_places(query, max_results))
    
    # 간결한 형식으로 변환
    simplified = []
    for p in places:
        simplified.append({
            "name": p.get("name", ""),
            "address": p.get("address", ""),
            "rating": p.get("rating", 0),
            "reviews": p.get("total_reviews", 0),
        })
    
    return json.dumps(simplified, ensure_ascii=False, indent=2)


# 동기 도구로 정의 (AgentExecutor 호환)
search_places_tool = StructuredTool.from_function(
    func=_search_places_sync,
    name="search_google_places",
    description="Google Places API로 장소를 검색합니다. query는 검색어, max_results는 결과 수입니다."
)


class MiniAgentFC:
    """
    LangChain Tool Calling 기반 미니 에이전트
    
    AgentExecutor를 사용하여 자동으로 도구를 호출합니다.
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        MiniAgentFC 초기화
        
        Args:
            model: Gemini 모델 이름
        """
        self.model_name = model or config.GEMINI_MODEL
        
        # LLM 초기화
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.7,
        )
        
        # 도구 정의
        self.tools = [search_places_tool]
        
        # 프롬프트 템플릿
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 친절한 장소 추천 전문가입니다.
사용자가 장소를 물어보면 search_google_places 도구를 사용해서 검색하세요.
검색 결과를 바탕으로 간결하게 3줄 이내로 요약해주세요.
반드시 이모지를 포함해서 친근하게 응답하세요."""),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Agent 생성
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True,
            handle_parsing_errors=True
        )
        
        print(f"🤖 MiniAgentFC 초기화 완료 (Model: {self.model_name})")
    
    @traceable(name="MiniAgentFC.run")
    async def run_async(
        self, 
        query: str, 
        max_places: int = 5
    ) -> Dict[str, Any]:
        """
        Tool Calling으로 장소 검색 및 응답 생성
        
        Args:
            query: 사용자 쿼리
            max_places: 최대 검색 결과 수
            
        Returns:
            {
                "query": 검색 쿼리,
                "places": 장소 정보 리스트,
                "answer": LLM 응답
            }
        """
        print(f"\n🚀 MiniAgentFC 실행: '{query}'")
        
        # AgentExecutor 실행
        result = await self.agent_executor.ainvoke({"input": query})
        
        answer = result.get("output", "응답을 생성할 수 없습니다.")
        
        print(f"\n✅ MiniAgentFC 완료")
        
        return {
            "query": query,
            "places": [],  # TODO: 도구 출력에서 추출
            "enriched_data": [],
            "answer": answer
        }
    
    def run(self, query: str, max_places: int = 5) -> Dict[str, Any]:
        """동기 버전"""
        return asyncio.run(self.run_async(query, max_places))


# 간편 사용 함수
async def run_mini_agent_fc(query: str, max_places: int = 5) -> Dict[str, Any]:
    """MiniAgentFC를 간편하게 실행하는 함수"""
    agent = MiniAgentFC()
    return await agent.run_async(query, max_places)


