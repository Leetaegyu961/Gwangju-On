from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from backend.db import get_database
from backend.models.user import UserTripSession, IntentContext, SurveyData, UserActivityLog

router = APIRouter()

class InvitationAcceptRequest(BaseModel):
    userId: str
    invitationId: str
    demographics: Optional[Dict[str, str]] = None

@router.post("/journey/accept-invitation")
async def accept_invitation(request: InvitationAcceptRequest):
    db = await get_database()
    
    # 초대장 기반의 초기 코스 데이터
    initial_course = {
        "course-1": {"title": "예술과 역사 코스", "region": "송정/동명"},
        "course-2": {"title": "예술가거리와 금남로 코스", "region": "금남로"},
        "course-3": {"title": "서구 8경 코스", "region": "서구"}
    }.get(request.invitationId, {"title": "맞춤 코스", "region": "광주전역"})

    # New Schema based on reward.md
    session_id = str(uuid.uuid4())
    survey_data = SurveyData(region=initial_course.get("region"), courses=[])
    intent_context = IntentContext(survey_data=survey_data, chat_history=[])
    
    new_session = UserTripSession(
        sessionId=session_id,
        userId=request.userId,
        status="IN_PROGRESS",
        intent_context=intent_context,
        album_data=[],
        created_at=datetime.now().isoformat(),
        last_activity_at=datetime.now().isoformat()
    )

    # Convert to dict for MongoDB
    session_dict = new_session.dict()
    
    await db["user_trip_sessions"].update_one(
        {"userId": request.userId}, # userId당 하나의 활성 세션 (또는 sessionId로 구분 가능)
        {"$set": session_dict},
        upsert=True
    )
    
    return {
        "status": "success",
        "message": "Invitation accepted and session created",
        "sessionId": session_id
    }

@router.post("/journey/status")
async def update_journey_status(user_id: str, status: str):
    db = await get_database()
    await db["user_trip_sessions"].update_one(
        {"userId": user_id},
        {"$set": {
            "status": status,
            "last_activity_at": datetime.now().isoformat()
        }}
    )
    return {"status": "success", "message": f"Journey status updated to {status}"}

class SaveFinalJourneyRequest(BaseModel):
    userId: str
    pickedPlaces: List[Dict]
    aiSummary: Optional[str] = None

@router.post("/journey/save-final")
async def save_final_journey(request: SaveFinalJourneyRequest):
    db = await get_database()
    
    update_data = {
        "status": "COMPLETED",
        "album_data": request.pickedPlaces,
        "ai_summary": request.aiSummary,
        "completed_at": datetime.now().isoformat(),
        "last_activity_at": datetime.now().isoformat()
    }
    
    await db["user_trip_sessions"].update_one(
        {"userId": request.userId},
        {"$set": update_data}
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
    actionType: str # PICK, SKIP, REJECT
    data: Dict
    sessionId: Optional[str] = None

@router.post("/journey/log-action")
async def log_silent_action(request: LogActionRequest):
    db = await get_database()
    
    # 1. user_activity_logs 컬렉션에 사일런트 기록
    log_entry = {
        "logId": str(uuid.uuid4()),
        "userId": request.userId,
        "sessionId": request.sessionId,
        "action_type": request.actionType,
        "data": request.data,
        "timestamp": datetime.now().isoformat()
    }
    await db["user_activity_logs"].insert_one(log_entry)
    
    # 2. 세션의 last_activity_at 업데이트
    await db["user_trip_sessions"].update_one(
        {"userId": request.userId},
        {"$set": {"last_activity_at": datetime.now().isoformat()}}
    )
    
    return {"status": "success", "message": f"{request.actionType} logged to user_activity_logs"}

@router.get("/journey/history/{userId}")
async def get_journey_history(userId: str):
    db = await get_database()
    # status가 COMPLETED인 모든 세션 조회 (최신순 정렬)
    cursor = db["user_trip_sessions"].find(
        {"userId": userId, "status": "COMPLETED"}
    ).sort("completed_at", -1)
    
    history = []
    async for doc in cursor:
        # _id 등 직렬화 불가능한 필드 처리
        doc["_id"] = str(doc["_id"])
        history.append(doc)
        
    return history

@router.delete("/journey/{sessionId}")
async def delete_journey(sessionId: str):
    db = await get_database()
    result = await db["user_trip_sessions"].delete_one({"sessionId": sessionId})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Journey not found")
        
    return {"status": "success", "message": "Journey deleted"}
