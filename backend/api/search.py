from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from backend.service.vector_search import search_vector_db

router = APIRouter(tags=["Search"])

@router.get("/search", summary="Search places using Vertex AI Vector Search")
async def search_places(
    q: str = Query(..., description="Search query (e.g., 'atmosphric pasta place')"),
    limit: int = Query(10, description="Number of results to return"),
    region: Optional[str] = Query(None, description="Filter by region (e.g., '동명동')")
):
    """
    Search for places using Google Cloud Vertex AI Vector Search.
    Uses 'text-multilingual-embedding-002' for high-quality semantic search in Korean.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query string is required")

    try:
        # Perform Vector Search
        results = search_vector_db(query=q, limit=limit)
        
        # Post-filtering by region (if needed, though Vector Search 'restricts' supports this natively)
        # Since our simple implementation does post-retrieval mapping, we can filter here too.
        if region:
            results = [r for r in results if region in r.get('region', '')]
            
        return {
            "query": q,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        print(f"Search API Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during search")
