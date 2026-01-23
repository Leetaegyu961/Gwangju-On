from fastapi import APIRouter, Response, HTTPException
import requests
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")

router = APIRouter()

@router.get("/photo")
async def get_google_photo(name: str):
    """
    Google Places API의 Photo Media를 프록시하여 반환합니다.
    Args:
        name: places/{PLACE_ID}/photos/{PHOTO_ID} 형식의 리소스 이름
    """
    if not name:
        raise HTTPException(status_code=400, detail="Photo Name is required")
        
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Server Configuration Error")

    # Google Places Photo API URL
    # 최대 크기 800px로 요청
    google_url = f"https://places.googleapis.com/v1/{name}/media?maxHeightPx=800&maxWidthPx=800&key={GOOGLE_API_KEY}"
    
    try:
        # Stream response from Google
        # 302 Redirect 대신 직접 이미지를 가져와서 반환 (Proxy)
        resp = requests.get(google_url, stream=True)
        if resp.status_code != 200:
             return Response(status_code=resp.status_code, content=resp.content)
        
        return Response(content=resp.content, media_type=resp.headers.get("Content-Type", "image/jpeg"))
        
    except Exception as e:
        print(f"Photo Proxy Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch image")
