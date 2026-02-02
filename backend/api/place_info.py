"""
Place Info API - Mini Agent 연동
가게 정보를 조회하는 간소화된 API 엔드포인트
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class PlaceInfoRequest(BaseModel):
    """장소 정보 요청"""
    place_name: str
    address: Optional[str] = ""


class PlaceInfoResponse(BaseModel):
    """장소 정보 응답"""
    name: str
    content: str
    img: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None


@router.post("/place-info", response_model=PlaceInfoResponse)
async def get_place_info(request: PlaceInfoRequest):
    """
    Mini Agent를 사용하여 장소 정보를 조회합니다.
    """
    from src.mini_agent import MiniAgent
    
    place_name = request.place_name
    address = request.address or ""
    
    # 주소에서 지역 정보 추출
    location_context = "광주"
    if address:
        parts = address.split()
        # 동 이름 찾기
        dong = next((p for p in parts if p.endswith("동") or p.endswith("가") or p.endswith("로")), None)
        if dong:
            location_context = dong
    
    # 검색 쿼리 생성
    query = f"{location_context} {place_name}"
    
    print(f"🔍 [PlaceInfo API] Query: {query}")
    
    try:
        agent = MiniAgent()
        result = await agent.run_async(query, max_places=1)
        
        # 결과에서 정보 추출
        answer = result.get("answer", "정보를 찾을 수 없습니다.")
        places = result.get("places", [])
        
        # 사진 URL 구성
        img_url = None
        rating = None
        reviews_count = None
        
        if places:
            first_place = places[0]
            if first_place.get("photo_name"):
                img_url = f"http://localhost:8000/api/photo?name={first_place['photo_name']}"
            rating = first_place.get("rating")
            reviews_count = first_place.get("total_reviews")
        
        print(f"✅ [PlaceInfo API] Response generated for: {place_name}")
        
        return PlaceInfoResponse(
            name=place_name,
            content=answer,
            img=img_url,
            rating=rating,
            reviews_count=reviews_count
        )
        
    except Exception as e:
        print(f"❌ [PlaceInfo API] Error: {e}")
        import traceback
        traceback.print_exc()
        
        return PlaceInfoResponse(
            name=place_name,
            content="정보를 불러오는 데 실패했어요. 잠시 후 다시 시도해주세요.",
            img=None
        )
