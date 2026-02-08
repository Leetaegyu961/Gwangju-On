"""
Mini Agent Nodes - Vector Search Node
VectorDB 기반 빠른 장소 검색 노드 (RAG 적용)
"""

from typing import Dict, Any, List


class VectorSearchNode:
    """
    VectorDB 기반 장소 검색 노드
    Google Places API 대신 미리 인덱싱된 데이터 사용으로 훨씬 빠름
    """
    
    def __init__(self):
        self._vector_db = None
    
    async def _get_vector_db(self):
        """VectorDB 지연 로딩 (싱글톤)"""
        if self._vector_db is None:
            from src.agent.tools.vector_db import GCPVectorDB
            self._vector_db = GCPVectorDB()
        return self._vector_db
    
    async def search(
        self, 
        query: str, 
        max_places: int = 5,
        region_filter: str = None
    ) -> List[Dict[str, Any]]:
        """
        VectorDB에서 장소 검색
        
        Args:
            query: 검색 쿼리 (예: "광주 동명동 맛집")
            max_places: 최대 검색 결과 수
            region_filter: 지역 필터 (예: "조대권", "시내권")
            
        Returns:
            장소 정보 리스트 (키워드, 평점 등 포함)
        """
        print(f"🔍 [VectorSearchNode] RAG 검색 시작: {query}")
        
        try:
            vector_db = await self._get_vector_db()
            
            # VectorDB 검색
            results = await vector_db.search(
                query=query, 
                k=max_places, 
                region_filter=region_filter
            )
            
            # 결과 포맷팅 (VectorDB 반환 구조에 맞게)
            # VectorDB는 place_name, keywords 등이 최상위 레벨에 있음
            places = []
            for item in results:
                keywords = item.get("keywords", {})
                
                place = {
                    "id": item.get("id", ""),
                    "name": item.get("place_name", "알 수 없음"),
                    "address": item.get("address", ""),
                    "rating": item.get("google_rating", 0) or item.get("rating", 0),
                    "total_reviews": item.get("total_reviews", 0),
                    "lat": item.get("lat", 0),
                    "lng": item.get("lng", 0),
                    # RAG 데이터 (키워드 기반)
                    "keywords": keywords,
                    "menu_type": keywords.get("menu_type", ""),
                    "signature_menu": keywords.get("signature_menu", []),
                    "ambiance": keywords.get("ambiance", []),
                    "special_features": keywords.get("special_features", []),
                    "recommended_for": keywords.get("recommended_for", []),
                    # 검색 점수
                    "similarity_score": item.get("similarity_score", 0),
                }
                places.append(place)
            
            print(f"✅ [VectorSearchNode] {len(places)}개 장소 검색 완료 (RAG)")
            return places
            
        except Exception as e:
            print(f"⚠️ [VectorSearchNode] 검색 오류: {e}")
            import traceback
            traceback.print_exc()
            return []

