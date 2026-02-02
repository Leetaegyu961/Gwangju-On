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
    # In-Memory DB나 DB에서 연령/성별 정보를 가져옴
    profile_data = USER_DB.get(user_id, {})
    
    demographics = {
        "age": profile_data.get("age"),
        "gender": profile_data.get("gender")
    }
    
    # 2. 신규 PRD 구조에 맞춘 데이터 패키징
    survey_data = {
        "region": survey.region,
        "courses": [c.dict() for c in survey.courses],
        "themes": survey.themes,
        "companions": survey.companions,
        "budget": survey.budget
    }
    
    session_doc = {
        "userId": user_id,
        "created_at": datetime.now().isoformat(),
        "demographics": demographics,
        "survey_data": survey_data,
        "chat_context": [],
        "status": "pending"
    }
    
    # 3. MongoDB 저장 (user_trip_sessions)
    await db["user_trip_sessions"].update_one(
        {"userId": user_id},
        {"$set": session_doc},
        upsert=True
    )
    
    # In-Memory DB (USER_DB) 에도 최신 상태 반영
    if user_id in USER_DB:
        USER_DB[user_id].update(survey.dict(exclude={"userId"}))
    else:
         USER_DB[user_id] = survey.dict(exclude={"userId"})
        
    return {"status": "success", "message": "Trip session started and saved to MongoDB."}

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
    cursor = db["user_archive"].find({"userId": user_id})
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