from fastapi import APIRouter, HTTPException, Body
from backend.db import get_database
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/session", tags=["Session"])

@router.post("/apply-invitation/{user_id}")
async def apply_invitation_to_session(user_id: str, payload: Dict[str, Any] = Body(...)):
    """
    초대장의 코스 데이터(album_data)를 
    사용자의 현재 세션(user_trip_sessions)에 덮어씌우거나 업데이트합니다.
    """
    db = await get_database()
    album_data = payload.get("album_data", [])
    
    if not album_data:
        raise HTTPException(status_code=400, detail="No album data provided")

    # 1. Update/Upsert Session
    # user_trip_sessions 컬렉션에서 user_id에 해당하는 status=IN_PROGRESS 세션을 찾아서 업데이트
    # 없으면 새로 생성? (일단 기존 세션 업데이트 위주)
    
    # Check for active session
    active_session = await db["user_trip_sessions"].find_one({
        "user_id": user_id,
        "status": "IN_PROGRESS"
    })
    
    new_context = {
        "user_id": user_id,
        "status": "IN_PROGRESS",
        "current_course": album_data, # 코스 주입
        "last_activity_at": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat()
    }

    if active_session:
        # Update existing
        await db["user_trip_sessions"].update_one(
            {"_id": active_session["_id"]},
            {"$set": {
                "current_course": album_data,
                "last_activity_at": datetime.now().isoformat()
            }}
        )
    else:
        # Create new session if not exists
        await db["user_trip_sessions"].insert_one(new_context)
    
    return {"message": "Session updated with invitation course", "course_len": len(album_data)}
