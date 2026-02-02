from fastapi import APIRouter
from backend.models.user import UserProfile, OnboardingResponse, SurveyResult
import uuid

from datetime import datetime

router = APIRouter()

# [In-Memory DB] 서버가 켜져있는 동안만 데이터가 유지됩니다.
# Key: user_id (str), Value: dict (profile + survey info)
USER_DB = {}

@router.post("/user/onboard", response_model=OnboardingResponse)
async def onboard_user(profile: UserProfile):
    # 1. 고유한 임시 ID 발급
    user_id = str(uuid.uuid4())
    
    # 2. 메모리에 저장
    USER_DB[user_id] = profile.dict()
    
    print(f"✅ [New User] ID: {user_id}, Profile: {USER_DB[user_id]}")
    
    # 3. ID 반환
    return OnboardingResponse(
        userId=user_id, 
        message="Profile saved to server memory."
    )

@router.post("/user/survey")
async def update_survey(survey: SurveyResult):
    user_id = survey.userId
    db = await get_database()
    
    # 1. 기존 유저 정보(Demographics) 가져오기
    profile_data = USER_DB.get(user_id, {})
    
    from backend.models.user import UserTripSession, IntentContext, SurveyData
    
    # 2. 신규 PRD 구조에 맞춘 데이터 패키징
    survey_data = SurveyData(
        region=survey.region,
        courses=survey.courses,
        themes=survey.themes,
        companions=survey.companions,
        budget=survey.budget,
        has_specific_place=survey.has_specific_place
    )
    
    # 3. 새로운 세션 구조 (reward.md 기반)
    session_id = str(uuid.uuid4())
    intent_context = IntentContext(survey_data=survey_data, chat_history=[])
    
    new_session = UserTripSession(
        sessionId=session_id,
        userId=user_id,
        status="IN_PROGRESS",
        intent_context=intent_context,
        album_data=[],
        created_at=datetime.now().isoformat(),
        last_activity_at=datetime.now().isoformat()
    )
    
    # 4. MongoDB 저장 (user_trip_sessions)
    await db["user_trip_sessions"].update_one(
        {"userId": user_id},
        {"$set": new_session.dict()},
        upsert=True
    )
    
    # In-Memory DB (USER_DB) 에도 최신 상태 반영
    if user_id in USER_DB:
        USER_DB[user_id].update(survey.dict(exclude={"userId"}))
    else:
        USER_DB[user_id] = survey.dict(exclude={"userId"})
        
    return {
        "status": "success",
        "message": "Trip session started with new schema.",
        "sessionId": session_id
    }

from backend.db import get_database
from backend.models.user import UserArchive

# (옵션) 저장된 정보 확인용 API (Memory + DB)
@router.get("/user/{user_id}")
async def get_user_profile(user_id: str):
    # 1. Check Memory (Guest)
    if user_id in USER_DB:
        return {"type": "guest", **USER_DB[user_id]}
    
    # 2. Check MongoDB (Google User)
    db = await get_database()
    user = await db["users"].find_one({"id": user_id})
    if user:
        # ObjectId -> str 변환 필요하지만 find_one은 dict 반환. _id 제외하고 반환 권장
        user.pop("_id", None)
        print(f"✅ [API] Found User in DB: {user_id}, Picture: {user.get('picture')}")
        return user
    
    print(f"❌ [API] User not found in DB: {user_id}")
    return {"error": "User not found"}

@router.get("/user/{user_id}/courses")
async def get_user_courses(user_id: str):
    db = await get_database()
    # owner_id 또는 userId 필드 확인. Frontend가 'userId'를 보내므로 모델 맞춤
    # 여기서 userId는 archive의 소유자
    cursor = db["user_archive"].find({"userId": user_id}).sort("createdAt", -1)
    courses = []
    async for doc in cursor:
        doc.pop("_id", None)
        courses.append(doc)
    return courses

@router.post("/user/courses")
async def save_user_course(course: UserArchive):
    db = await get_database()
    course_dict = course.dict()
    # 이미 존재하는지 확인 (id 기준)
    existing = await db["user_archive"].find_one({"id": course.id})
    if existing:
        await db["user_archive"].update_one({"id": course.id}, {"$set": course_dict})
        return {"message": "Course updated", "id": course.id}
    else:
        await db["user_archive"].insert_one(course_dict)
        return {"message": "Course saved", "id": course.id}