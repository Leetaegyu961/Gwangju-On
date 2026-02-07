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

class CourseData(BaseModel):
    course_id: Optional[str] = None
    course_name: str
    course_description: Optional[str] = None
    places: List[Dict]

class SaveFinalJourneyRequest(BaseModel):
    userId: str
    selectedCourseIndex: Optional[int] = -1
    allCourses: List[CourseData]
    customPlaces: Optional[List[Dict]] = None # 사용자가 직접 섞어 만든 코스 (장소 리스트)
    aiSummary: Optional[str] = None

@router.post("/journey/save-final")
async def save_final_journey(request: SaveFinalJourneyRequest):
    db = await get_database()
    
    group_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    saved_count = 0
    sessions_to_return = []
    
    # 1. 원본 추천 코스 3개 모두 저장 (Candidates)
    # 1. 원본 추천 코스 3개 모두 저장 (Candidates)
    if request.allCourses:
        for idx, course in enumerate(request.allCourses):
            # 사용자가 커스텀 코스를 만들지 않고, 그냥 1개를 선택했을 경우
            is_selected_original = (not request.customPlaces) and (idx == request.selectedCourseIndex)
            
            # [Fix] 기존 세션이 있는지 확인 (중복 저장 방지 - 사용자 요청)
            existing_session = None
            if course.course_id:
                # course_id가 "1"(임시) 같은 게 아니라 진짜 UUID인지 확인 필요하지만, DB 조회하면 알아서 걸러짐
                existing_session = await db["user_trip_sessions"].find_one({"sessionId": course.course_id})
                
            if existing_session:
                # Update existing
                await db["user_trip_sessions"].update_one(
                    {"sessionId": course.course_id},
                    {"$set": {
                        "status": "COMPLETED" if is_selected_original else "COMPLETED_CANDIDATE",
                        "is_selected": is_selected_original,
                        "title": course.course_name, 
                        "last_activity_at": timestamp,
                        "timeline_generated": False # [Mod] 타임라인 즉시 생성 방지
                    }}
                )
                sessions_to_return.append({"sessionId": course.course_id, "title": course.course_name})
                # saved_count는 insert한 게 아니므로 증가 안 시키거나, 로직에 따라 다름. 여기선 skip.
            else:
                new_journey = {
                    "sessionId": str(uuid.uuid4()),
                    "group_id": group_id,
                    "userId": request.userId,
                    "status": "COMPLETED" if is_selected_original else "COMPLETED_CANDIDATE",
                    "is_selected": is_selected_original,
                    "title": course.course_name,
                    "course_description": course.course_description,
                    "album_data": course.places,
                    "total_courses": len(course.places),
                    "ai_summary": request.aiSummary if is_selected_original else "AI 추천 후보 코스",
                    "created_at": timestamp,
                    "completed_at": timestamp,
                    "last_activity_at": timestamp,
                    "last_activity_at": timestamp,
                    "intent_context": {},
                    "timeline_generated": False # [Mod] 타임라인 즉시 생성 방지 
                }
                await db["user_trip_sessions"].insert_one(new_journey)
                saved_count += 1
                sessions_to_return.append(new_journey)

    # 2. 사용자가 섞어 만든 커스텀 코스 저장 (Selected)
    if request.customPlaces and len(request.customPlaces) > 0:
        custom_journey = {
            "sessionId": str(uuid.uuid4()),
            "group_id": group_id,
            "userId": request.userId,
            "status": "COMPLETED",
            "is_selected": True,
            "title": f"나만의 커스텀 여행 ({datetime.now().strftime('%m/%d')})",
            "course_description": "직접 선택한 장소들로 구성된 여행 코스입니다.",
            "album_data": request.customPlaces,
            "total_courses": len(request.customPlaces),
            "ai_summary": request.aiSummary or "사용자 정의 코스",
            "created_at": timestamp,
            "completed_at": timestamp,
            "last_activity_at": timestamp,
            "intent_context": {},
            "timeline_generated": False # [Mod] 타임라인 즉시 생성 방지 
        }
        await db["user_trip_sessions"].insert_one(custom_journey)
        saved_count += 1
        sessions_to_return.append(custom_journey)
    
    return {
        "status": "success",
        "message": f"Saved {saved_count} courses to history",
        "group_id": group_id,
        "timestamp": timestamp,
        # [Fix] Return Session IDs for frontend to sync
        "saved_sessions": [
             {"sessionId": s.get("sessionId"), "title": s.get("title")} 
             for s in (sessions_to_return if 'sessions_to_return' in locals() else [])
        ]
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
    # status가 COMPLETED 또는 COMPLETED_CANDIDATE인 모든 세션 조회
    cursor = db["user_trip_sessions"].find(
        {
            "userId": userId, 
            "status": {"$in": ["COMPLETED", "COMPLETED_CANDIDATE"]}
        }
    ).sort("completed_at", -1)
    
    history = []
    async for doc in cursor:
        # _id 등 직렬화 불가능한 필드 처리
        doc["_id"] = str(doc["_id"])
        
        # [Fix] ID Mapping (Frontend uses 'id' as key)
        # sessionId가 있으면 쓰고, 없으면 _id를 사용
        doc["id"] = str(doc.get("sessionId") or doc["_id"])
        
        # [Mapping] Frontend compatibility (SavedCourse interface)
        if "album_data" in doc:
            doc["points"] = doc["album_data"]
        else:
            doc["points"] = []
            
        if "total_courses" not in doc:
            doc["total_courses"] = len(doc["points"])
            
        # Default budget String if missing
        if "totalBudget" not in doc:
             doc["totalBudget"] = "예산 산출 중"
             
        # [Fix] Date mapping (camelCase for frontend)
        if "created_at" in doc and "createdAt" not in doc:
             doc["createdAt"] = doc["created_at"]
             
        # [Fix] Description mapping
        if "course_description" in doc and "description" not in doc:
             doc["description"] = doc["course_description"]
        
        # [Fix] Group ID Mapping (for restoring full recommendation set)
        if "group_id" in doc:
             doc["groupId"] = doc["group_id"]
        
        # [Fix] Timeline Generated 필드 (기본값 False)
        if "timeline_generated" not in doc:
             doc["timeline_generated"] = False
            
        history.append(doc)
        
    return history

@router.delete("/journey/{sessionId}")
async def delete_journey(sessionId: str):
    db = await get_database()
    result = await db["user_trip_sessions"].delete_one({"sessionId": sessionId})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Journey not found")
        
    return {"status": "success", "message": "Journey deleted"}

@router.patch("/journey/{sessionId}/unselect")
async def unselect_course(sessionId: str):
    """확정한 코스에서 제거 (is_selected를 false로 변경)"""
    db = await get_database()
    result = await db["user_trip_sessions"].update_one(
        {"sessionId": sessionId},
        {"$set": {"is_selected": False, "updated_at": datetime.utcnow().isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Journey not found")
        
    return {"status": "success", "message": "Course unselected"}

@router.patch("/journey/{sessionId}/remove-timeline")
async def remove_timeline(sessionId: str):
    """타임라인에서 제거 (timeline_generated를 false로 변경)"""
    db = await get_database()
    result = await db["user_trip_sessions"].update_one(
        {"sessionId": sessionId},
        {"$set": {"timeline_generated": False, "updated_at": datetime.utcnow().isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Journey not found")
        
    return {"status": "success", "message": "Timeline removed"}


class CreateTimelineRequest(BaseModel):
    userId: str
    memorySpots: List[Dict[str, Any]]
    tastingNotes: Dict[str, Any]

@router.post("/journey/{course_id}/create-timeline")
async def create_timeline(course_id: str, request: CreateTimelineRequest):
    """
    테이스팅 노트 완성 후 타임라인 생성
    - timeline_generated를 true로 업데이트
    - 추억 남긴 장소들을 저장
    - 코스가 없으면 새로 생성 (upsert)
    """
    db = await get_database()
    
    # timeline_generated를 true로 업데이트 (없으면 생성)
    result = await db["user_trip_sessions"].update_one(
        {"sessionId": course_id},
        {"$set": {
            "sessionId": course_id,
            "userId": request.userId,
            "timeline_generated": True,
            "memory_spots": request.memorySpots,
            "tasting_notes": request.tastingNotes,
            "timeline_created_at": datetime.utcnow().isoformat(),
            "is_selected": True,  # 확정된 코스
            "status": "COMPLETED",
            "updated_at": datetime.utcnow().isoformat()
        }},
        upsert=True  # 없으면 새로 생성
    )
    
    return {
        "status": "success",
        "message": "Timeline created successfully",
        "course_id": course_id,
        "memory_spots_count": len(request.memorySpots),
        "upserted": result.upserted_id is not None
    }

