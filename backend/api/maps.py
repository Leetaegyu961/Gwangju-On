from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import requests
import os
from pydantic import BaseModel
from typing import List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# [Debug] API Key Check
if not GOOGLE_MAPS_API_KEY:
    print("❌ [Maps API] GOOGLE_MAPS_API_KEY is missing in .env")
else:
    print(f"✅ [Maps API] GOOGLE_MAPS_API_KEY loaded (len: {len(GOOGLE_MAPS_API_KEY)})")

class Marker(BaseModel):
    lat: float
    lng: float
    label: Optional[str] = None

class StaticMapRequest(BaseModel):
    center: Optional[dict] = None  # {"lat": ..., "lng": ...}
    zoom: Optional[int] = None
    markers: List[Marker] = []
    path: List[dict] = []  # [{"lat":..., "lng":...}]
    size: str = "600x400"
    maptype: str = "roadmap"

@router.post("/maps/static")
async def get_static_map_image(req: StaticMapRequest):
    if not GOOGLE_MAPS_API_KEY:
        print("❌ [Maps API] Error: GOOGLE_MAPS_API_KEY is not set.")
        raise HTTPException(status_code=500, detail="GOOGLE_MAPS_API_KEY not configured")

    url = "https://maps.googleapis.com/maps/api/staticmap"
    
    # 디버깅: 요청 정보 출력
    # print(f"📍 [Maps API] Request: {len(req.markers)} markers, Center: {req.center}")

    # 기본 파라미터 (리스트 튜플로 변환하여 중복 키 허용)
    query_params = [
        ("size", req.size),
        ("maptype", req.maptype),
        ("key", GOOGLE_MAPS_API_KEY),
        ("language", "ko"),
        ("scale", "2")
    ]

    if req.center:
        query_params.append(("center", f"{req.center['lat']},{req.center['lng']}"))
    
    if req.zoom:
        query_params.append(("zoom", str(req.zoom)))

    # Markers 추가
    for i, m in enumerate(req.markers):
        # 기본 스타일: 오렌지색, 숫자 라벨
        label = m.label if m.label else str(i + 1)
        # Google Static Maps는 라벨로 한 자리 숫자나 알파벳 대문자만 공식 지원하지만,
        # 일부 경우 두 자리도 렌더링되거나 무시될 수 있음. 안전하게 한 자리만 쓰거나 라벨 생략 가능.
        # 여기서는 그대로 둠.
        marker_value = f"color:orange|label:{label}|{m.lat},{m.lng}"
        query_params.append(("markers", marker_value))

    # Path 추가
    if req.path and len(req.path) > 0:
        path_str = "color:0xFF6B00FF|weight:5"
        for p in req.path:
            path_str += f"|{p['lat']},{p['lng']}"
        query_params.append(("path", path_str))
    
    try:
        # Stream=True로 이미지 받아오기, 타임 5초
        response = requests.get(url, params=query_params, stream=True, timeout=10)
        
        # 에러 응답인 경우 본문 읽어서 출력
        if response.status_code != 200:
            error_text = response.text
            print(f"❌ [Maps API] Google Error ({response.status_code}): {error_text}")
            raise HTTPException(status_code=500, detail=f"Google API Error: {error_text}")

        # 이미지 데이터 반환
        return Response(content=response.content, media_type="image/png")
        
    except requests.RequestException as e:
        print(f"❌ [Maps API] Request Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"❌ [Maps API] Unexpected Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
