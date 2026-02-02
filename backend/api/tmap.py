from fastapi import APIRouter, HTTPException, Query
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

TMAP_APP_KEY = os.getenv("TMAP_APP_KEY")

@router.get("/tmap/poi/around")
def search_poi_around(
    keyword: str = Query(..., description="Search keyword or category"),
    lat: float = Query(..., description="Center latitude"),
    lng: float = Query(..., description="Center longitude"),
    radius: int = Query(1, description="Radius in km"),
    count: int = Query(20, description="Number of results")
):
    if not TMAP_APP_KEY:
        raise HTTPException(status_code=500, detail="TMAP_APP_KEY not configured")

    # /pois endpoint is better for keyword-focused search within radius
    url = "https://apis.openapi.sk.com/tmap/pois/search/around"
    
    # Using searchKeyword handles text queries like "맛집", "카페" much better than categories param
    # which expects codes.
    params = {
        "version": 1,
        "format": "json",
        "searchKeyword": keyword,
        "centerLat": lat,
        "centerLon": lng,
        "radius": radius,
        "count": count,
        "appKey": TMAP_APP_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Tmap External API Error: {e}")
        # Return empty result or error depending on preference.
        # Returning error helps debugging.
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tmap/poi/search")
def search_poi(
    keyword: str = Query(..., description="Search keyword"),
    count: int = Query(20, description="Number of results")
):
    if not TMAP_APP_KEY:
        raise HTTPException(status_code=500, detail="TMAP_APP_KEY not configured")

    url = "https://apis.openapi.sk.com/tmap/pois"
    params = {
        "version": 1,
        "format": "json",
        "searchKeyword": keyword,
        "count": count,
        "appKey": TMAP_APP_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Tmap POI Search Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tmap/geo/reverse")
def reverse_geocoding(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude")
):
    if not TMAP_APP_KEY:
        raise HTTPException(status_code=500, detail="TMAP_APP_KEY not configured")

    # TMAP Reverse Geocoding API
    url = "https://apis.openapi.sk.com/tmap/geo/reversegeocoding"
    
    params = {
        "version": 1,
        "lat": lat,
        "lon": lng,
        "coordType": "WGS84GEO",
        "addressType": "A04", # A04: Building name priority
        "appKey": TMAP_APP_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Tmap Reverse Geo Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
