"""
Mini Agent - Main Agent
LangChain + Gemini를 사용한 간소화된 장소 정보 에이전트

노드 구조:
1. PlaceSearchNode - Google Places API 검색
2. LLMNode - 장소 정보 요약 생성

LangSmith에서 각 노드가 독립적으로 추적됩니다.
"""

import asyncio
from typing import Dict, Any, Optional

from langsmith import traceable

from .nodes import PlaceSearchNode, LLMNode


class MiniAgent:
    """
    간소화된 장소 정보 에이전트
    
    노드 기반 아키텍처로 LangSmith 추적이 용이합니다.
    
    사용법:
        agent = MiniAgent()
        result = await agent.run_async("광주 동명동 맛집")
        # 또는 동기 버전
        result = agent.run("광주 동명동 맛집")
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        MiniAgent 초기화
        
        Args:
            model: Gemini 모델 이름 (기본값: config에서 가져옴)
        """
        # 노드 초기화
        self.place_search_node = PlaceSearchNode()
        self.llm_node = LLMNode(model=model)
        
        print(f"🤖 MiniAgent 초기화 완료 (Model: {self.llm_node.model_name})")
    
    @traceable(name="MiniAgent.run")
    async def run_async(
        self, 
        query: str, 
        max_places: int = 5
    ) -> Dict[str, Any]:
        """
        비동기로 장소 검색 및 LLM 응답 생성
        
        Args:
            query: 검색 쿼리 (예: "광주 동명동 맛집")
            max_places: 검색할 최대 장소 수
            
        Returns:
            {
                "query": 검색 쿼리,
                "places": 장소 정보 리스트,
                "enriched_data": 장소 정보,
                "answer": LLM 응답
            }
        """
        print(f"\n🚀 MiniAgent 실행: '{query}'")
        
        # Step 1: Google Place 검색 (PlaceSearchNode)
        places = await self._run_place_search(query, max_places)
        
        if not places:
            return {
                "query": query,
                "places": [],
                "enriched_data": [],
                "answer": "검색 결과가 없습니다."
            }
        
        # Step 2: LLM 응답 생성 (LLMNode)
        answer = await self._run_llm_summary(query, places)
        
        print(f"\n✅ MiniAgent 완료")
        
        return {
            "query": query,
            "places": places,
            "enriched_data": [{"place": p, "blogs": []} for p in places],
            "answer": answer
        }
    
    @traceable(name="MiniAgent.PlaceSearch")
    async def _run_place_search(
        self, 
        query: str, 
        max_places: int
    ) -> list:
        """Step 1: 장소 검색 (LangSmith 추적)"""
        print(f"\n📍 Step 1: Google Place 검색")
        return await self.place_search_node.search(query, max_places)
    
    @traceable(name="MiniAgent.LLMSummary")
    async def _run_llm_summary(
        self, 
        query: str, 
        places: list
    ) -> str:
        """Step 2: LLM 요약 생성 (LangSmith 추적)"""
        print(f"\n🧠 Step 2: LLM 응답 생성")
        return await self.llm_node.generate_summary(query, places)
    
    def run(self, query: str, max_places: int = 5) -> Dict[str, Any]:
        """
        동기 버전의 실행 메서드
        
        Args:
            query: 검색 쿼리
            max_places: 검색할 최대 장소 수
            
        Returns:
            run_async와 동일한 결과
        """
        return asyncio.run(self.run_async(query, max_places))


# 간편 사용을 위한 함수
async def run_mini_agent(query: str, max_places: int = 5) -> Dict[str, Any]:
    """MiniAgent를 간편하게 실행하는 함수"""
    agent = MiniAgent()
    return await agent.run_async(query, max_places)


