"""
Mini Agent Nodes - Place Search Node
LangSmith 추적을 위한 독립적인 장소 검색 노드
"""

from typing import Dict, Any, List
from ..place_search import search_places


class PlaceSearchNode:
    """
    Google Places API 검색 노드
    LangSmith에서 독립적으로 추적됩니다.
    """
    
    async def search(
        self, 
        query: str, 
        max_places: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Google Places API로 장소 검색
        
        Args:
            query: 검색 쿼리 (예: "광주 동명동 맛집")
            max_places: 최대 검색 결과 수
            
        Returns:
            장소 정보 리스트
        """
        print(f"📍 [PlaceSearchNode] 검색 시작: {query}")
        
        try:
            places = await search_places(query, max_places)
            print(f"✅ [PlaceSearchNode] {len(places)}개 장소 검색 완료")
            return places
        except Exception as e:
            print(f"⚠️ [PlaceSearchNode] 검색 오류: {e}")
            return []
