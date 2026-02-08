"""
Vector Retrieval Node
GCP Vertex AI Vector Search를 사용하여 사전에 인덱싱된 장소들을 검색하는 노드입니다.
(Parallel Hybrid RAG: Fan-Out Phase 1 - Semantic Search)
"""

from typing import Any
import asyncio
from ..state import AgentState
from ..tools.vector_db import vector_db

async def vector_retrieval_node(state: AgentState) -> dict[str, Any]:
    """
    Vector DB 검색을 수행하여 의미적으로 유사한 장소들을 찾습니다.
    (Pure Retrieval: API 호출 없이 Vector DB만 조회)
    
    Args:
        state: AgentState (query_plan, survey_data 포함)
        
    Returns:
        dict: {"vector_candidates": [...]}
    """
    query_plan = state.get("query_plan", {})
    if not query_plan:
        print("[VectorRetrieval] ⚠️ Query Plan 없음. 스킵합니다.")
        return {"vector_candidates": []}

    queries = query_plan.get("place_queries", [])
    if not queries:
        # Fallback if specific queries are missing
        themes = state.get("themes", [])
        if themes:
            queries = themes
        else:
            print("[VectorRetrieval] ⚠️ 검색 쿼리 없음. 스킵합니다.")
            return {"vector_candidates": []}

    # Region Filter logic
    survey_data = state.get("survey_data", {})
    region_filter = survey_data.get("region")
    
    if region_filter and region_filter in ["광주 전체", "모름", "상관없음"]:
        region_filter = None
    
    print(f"[VectorRetrieval] 🔍 검색 시작: 쿼리 {len(queries)}개, 지역필터={region_filter}")

    # Deduplicate queries
    unique_queries = list(set(queries))
    
    # Parallel Search
    # k=20으로 수정 (최적화: 쿼리당 결과 수 감소)
    search_tasks = [
        vector_db.search(q, k=20, region_filter=region_filter)
        for q in unique_queries
    ]
    
    results_list = await asyncio.gather(*search_tasks)
    
    # Flatten and Deduplicate Results
    all_results = []
    seen_ids = set()
    
    for results in results_list:
        for item in results:
            # item has 'id', 'place_name', 'similarity_score', 'data'
            # Assuming 'place_name' is unique enough or use 'id'
            pid = item.get("id") or item.get("place_name")
            
            if pid and pid not in seen_ids:
                all_results.append(item)
                seen_ids.add(pid)
    
    print(f"[VectorRetrieval] ✅ 총 {len(all_results)}개 고유 장소 발견")
    
    return {"vector_candidates": all_results}
