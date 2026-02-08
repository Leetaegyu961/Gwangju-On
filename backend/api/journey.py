from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from backend.db import get_database
from backend.models.user import UserTripSession, IntentContext, SurveyData, UserActivityLog
from backend.api.preference_utils import learn_from_course_selection, learn_from_discovery_action

router = APIRouter()

class InvitationAcceptRequest(BaseModel):
    userId: str
    invitationId: str
    demographics: Optional[Dict[str, str]] = None

@router.post("/journey/accept-invitation")
async def accept_invitation(request: InvitationAcceptRequest):
    db = await get_database()

    initial_course = {
        "course-1": {"title": "예술과 역사 코스", "region": "송정/동명"},
        "course-2": {"title": "예술가거리와 금남로 코스", "region": "금남로"},
        "course-3": {"title": "서구 8경 코스", "region": "서구"}
    }.get(request.invitationId, {"title": "맞춤 코스", "region": "광주전역"})

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

    session_dict = new_session.dict()

    await db["user_trip_sessions"].update_one(
        {"userId": request.userId},
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
    customPlaces: Optional[List[Dict]] = None
    aiSummary: Optional[str] = None

@router.post("/journey/save-final")
async def save_final_journey(request: SaveFinalJourneyRequest):
    db = await get_database()

    group_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    saved_count = 0
    sessions_to_return = []

    if request.allCourses:
        for idx, course in enumerate(request.allCourses):
            is_selected_original = (not request.customPlaces) and (idx == request.selectedCourseIndex)

            existing_session = None
            if course.course_id:
                existing_session = await db["user_trip_sessions"].find_one({"sessionId": course.course_id})

            if existing_session:
                await db["user_trip_sessions"].update_one(
                    {"sessionId": course.course_id},
                    {"$set": {
                        "status": "COMPLETED" if is_selected_original else "COMPLETED_CANDIDATE",
                        "is_selected": is_selected_original,
                        "title": course.course_name,
                        "last_activity_at": timestamp,
                        "timeline_generated": False
                    }}
                )
                sessions_to_return.append({"sessionId": course.course_id, "title": course.course_name})
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
                    "intent_context": {},
                    "timeline_generated": False
                }
                await db["user_trip_sessions"].insert_one(new_journey)
                saved_count += 1
                sessions_to_return.append(new_journey)

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
            "timeline_generated": False
        }
        await db["user_trip_sessions"].insert_one(custom_journey)
        saved_count += 1
        sessions_to_return.append(custom_journey)

    # [Preference Learning] 확정한 코스의 장소 태그로부터 선호도 점진 학습
    if request.allCourses and request.userId:
        try:
            for idx, course in enumerate(request.allCourses):
                is_selected = (not request.customPlaces) and (idx == request.selectedCourseIndex)
                if is_selected:
                    await learn_from_course_selection(db, request.userId, course.places)
        except Exception as e:
            print(f"⚠️ [Preference Learning] save-final failed: {e}")

    if request.customPlaces and request.userId:
        try:
            await learn_from_course_selection(db, request.userId, request.customPlaces)
        except Exception as e:
            print(f"⚠️ [Preference Learning] custom-course failed: {e}")

    return {
        "status": "success",
        "message": f"Saved {saved_count} courses to history",
        "group_id": group_id,
        "timestamp": timestamp,
        "saved_sessions": [
             {"sessionId": s.get("sessionId"), "title": s.get("title")}
             for s in sessions_to_return
        ]
    }

class SaveWishlistRequest(BaseModel):
    userId: str
    courseData: Dict

@router.post("/journey/save-wishlist")
async def save_wishlist(request: SaveWishlistRequest):
    db = await get_database()

    await db["user_wishlist"].update_one(
        {"userId": request.userId},
        {"$push": {"wishlist": {
            "course": request.courseData,
            "saved_at": datetime.now().isoformat()
        }}},
        upsert=True
    )

    return {"status": "success", "message": "Course saved to wishlist"}

@router.get("/journey/wishlist/{userId}")
async def get_wishlist(userId: str):
    db = await get_database()
    doc = await db["user_wishlist"].find_one({"userId": userId})
    if not doc:
        return {"wishlist": []}
    if "_id" in doc:
        doc.pop("_id")
    return {"wishlist": doc.get("wishlist", [])}

@router.get("/journey/session/{userId}")
async def get_session(userId: str):
    db = await get_database()
    session = await db["user_trip_sessions"].find_one({"userId": userId})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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

    log_entry = {
        "logId": str(uuid.uuid4()),
        "userId": request.userId,
        "sessionId": request.sessionId,
        "action_type": request.actionType,
        "data": request.data,
        "timestamp": datetime.now().isoformat()
    }
    await db["user_activity_logs"].insert_one(log_entry)

    await db["user_trip_sessions"].update_one(
        {"userId": request.userId},
        {"$set": {"last_activity_at": datetime.now().isoformat()}}
    )

    # [Preference Learning] PICK/SKIP/REJECT 행동에서 선호도 미세 학습
    try:
        category = request.data.get("category", "")
        await learn_from_discovery_action(db, request.userId, request.actionType, category)
    except Exception as e:
        print(f"⚠️ [Preference Learning] log-action failed: {e}")

    return {"status": "success", "message": f"{request.actionType} logged to user_activity_logs"}

@router.get("/journey/history/{userId}")
async def get_journey_history(userId: str):
    db = await get_database()
    cursor = db["user_trip_sessions"].find(
        {
            "userId": userId,
            "status": {"$in": ["COMPLETED", "COMPLETED_CANDIDATE"]}
        }
    ).sort("completed_at", -1)

    history = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])

        doc["id"] = str(doc.get("sessionId") or doc["_id"])

        if "album_data" in doc:
            doc["points"] = doc["album_data"]
        else:
            doc["points"] = []

        if "total_courses" not in doc:
            doc["total_courses"] = len(doc["points"])

        if "totalBudget" not in doc:
             doc["totalBudget"] = "예산 산출 중"

        if "created_at" in doc and "createdAt" not in doc:
             doc["createdAt"] = doc["created_at"]

        if "course_description" in doc and "description" not in doc:
             doc["description"] = doc["course_description"]

        if "group_id" in doc:
             doc["groupId"] = doc["group_id"]

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
    """
    db = await get_database()

    result = await db["user_trip_sessions"].update_one(
        {"sessionId": course_id},
        {"$set": {
            "sessionId": course_id,
            "userId": request.userId,
            "timeline_generated": True,
            "memory_spots": request.memorySpots,
            "tasting_notes": request.tastingNotes,
            "timeline_created_at": datetime.utcnow().isoformat(),
            "is_selected": True,
            "status": "COMPLETED",
            "updated_at": datetime.utcnow().isoformat()
        }},
        upsert=True
    )

    return {
        "status": "success",
        "message": "Timeline created successfully",
        "course_id": course_id,
        "memory_spots_count": len(request.memorySpots),
        "upserted": result.upserted_id is not None
    }
