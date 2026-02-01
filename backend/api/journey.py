from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from backend.db import get_database

router = APIRouter()

class InvitationAcceptRequest(BaseModel):
    userId: str
    invitationId: str
    demographics: Optional[Dict[str, str]] = None

@router.post("/journey/accept-invitation")
async def accept_invitation(request: InvitationAcceptRequest):
    db = await get_database()
    
    # 초대장 기반의 초기 코스 데이터 (임시 폴백)
    initial_course = {
        "course-1": {"title": "예술과 역사 코스", "region": "송정/동명"},
        "course-2": {"title": "예술가거리와 금남로 코스", "region": "금남로"},
        "course-3": {"title": "서구 8경 코스", "region": "서구"}
    }.get(request.invitationId, {"title": "맞춤 코스", "region": "광주전역"})

    new_session = {
        "userId": request.userId,
        "invitationId": request.invitationId,
        "performed_course_id": request.invitationId, # 수락된 코스 기록
        "status": "IN_PROGRESS",
        "albumStatus": "IN_PROGRESS",
        "created_at": datetime.now().isoformat(),
        "demographics": request.demographics,
        "survey_data": initial_course,
        "chat_context": [],
        "album_data": [],
        "tasting_notes": None,
        "rejected_invitations": [], # 반려 이력
        "picked_places": [],        # 담기 이력
        "skipped_places": [],       # 물색 이력
        "tasting_note_raw": {}      # 테이스팅 노트 날것의 데이터
    }

    result = await db["user_trip_sessions"].update_one(
        {"userId": request.userId},
        {"$set": new_session},
        upsert=True
    )
    
    return {
        "status": "success",
        "message": "Invitation accepted and session created",
        "sessionId": request.userId # userId를 세션 ID로 병행 사용
    }

@router.post("/journey/status")
async def update_journey_status(user_id: str, status: str):
    db = await get_database()
    await db["user_trip_sessions"].update_one(
        {"userId": user_id},
        {"$set": {"status": status}}
    )
    return {"status": "success", "message": f"Journey status updated to {status}"}

@router.post("/journey/album-status")
async def update_album_status(user_id: str, status: str):
    db = await get_database()
    await db["user_trip_sessions"].update_one(
        {"userId": user_id},
        {"$set": {"albumStatus": status}}
    )
    return {"status": "success", "message": f"Album status updated to {status}"}

class SaveFinalJourneyRequest(BaseModel):
    userId: str
    pickedPlaces: List[Dict]
    aiSummary: Optional[str] = None

@router.post("/journey/save-final")
async def save_final_journey(request: SaveFinalJourneyRequest):
    db = await get_database()
    
    update_data = {
        "status": "COMPLETED",
        "albumStatus": "SAVED",
        "album_data": request.pickedPlaces,
        "ai_summary": request.aiSummary,
        "completed_at": datetime.now().isoformat()
    }
    
    await db["user_trip_sessions"].update_one(
        {"userId": request.userId},
        {"$set": update_data},
        upsert=True
    )
    
    return {
        "status": "success",
        "message": "Journey saved successfully",
        "timestamp": update_data["completed_at"]
    }

class SaveWishlistRequest(BaseModel):
    userId: str
    courseData: Dict

@router.post("/journey/save-wishlist")
async def save_wishlist(request: SaveWishlistRequest):
    db = await get_database()
    
    # user_wishlist 컬렉션에 저장
    await db["user_wishlist"].update_one(
        {"userId": request.userId},
        {"$push": {"wishlist": {
            "course": request.courseData,
            "saved_at": datetime.now().isoformat()
        }}},
        upsert=True
    )
    
    return {"status": "success", "message": "Course saved to wishlist"}

@router.get("/journey/session/{userId}")
async def get_session(userId: str):
    db = await get_database()
    session = await db["user_trip_sessions"].find_one({"userId": userId})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert ObjectId to string if present
    if "_id" in session:
        session["_id"] = str(session["_id"])
        
    return session

class LogActionRequest(BaseModel):
    userId: str
    actionType: str # REJECT_INVITATION, PICK_PLACE, SKIP_PLACE
    data: Dict

@router.post("/journey/log-action")
async def log_silent_action(request: LogActionRequest):
    db = await get_database()
    
    field_map = {
        "REJECT_INVITATION": "rejected_invitations",
        "PICK_PLACE": "picked_places",
        "SKIP_PLACE": "skipped_places"
    }
    
    field = field_map.get(request.actionType)
    if not field:
        raise HTTPException(status_code=400, detail="Invalid action type")
    
    # 사실 기반 데이터 로깅 (비개입성)
    update_data = {
        "$push": {field: {
            "data": request.data,
            "logged_at": datetime.now().isoformat()
        }}
    }
    
    await db["user_trip_sessions"].update_one(
        {"userId": request.userId},
        update_data,
        upsert=True
    )
    
    return {"status": "success", "message": f"{request.actionType} logged"}
