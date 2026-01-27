from fastapi import APIRouter, HTTPException
from backend.models.user import UserProfile, OnboardingResponse, SurveyResult
from backend.db import get_database
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/user/onboard", response_model=OnboardingResponse)
async def onboard_user(profile: UserProfile):
    # 1. 고유한 임시 ID 발급 (Guest ID)
    user_id = str(uuid.uuid4())
    
    db = await get_database()
    guests_col = db["guests"]
    
    # 2. guests 컬렉션에 저장 (TTL 적용 대상)
    guest_data = {
        "id": user_id,
        "is_guest": True,
        "profile": profile.dict(),
        "created_at": datetime.utcnow(),
        "last_active_at": datetime.utcnow() # TTL index용
    }
    await guests_col.insert_one(guest_data)
    
    print(f"✅ [New Guest] ID: {user_id} (Stored in 'guests' collection)")
    
    return OnboardingResponse(
        userId=user_id, 
        message="Guest profile saved to guests collection."
    )

@router.put("/user/profile")
async def update_user_profile(profile: UserProfile, userId: str):
    db = await get_database()
    users_col = db["users"]
    
    result = await users_col.update_one(
        {"id": userId},
        {"$set": {
            "profile": profile.dict(),
            "last_updated": datetime.utcnow()
        }}
    )
    
    if result.matched_count == 0:
        # 회원이 아닐 경우 게스트 컬렉션에서 시도 (또는 에러 처리)
        guests_col = db["guests"]
        await guests_col.update_one(
            {"id": userId},
            {"$set": {
                "profile": profile.dict(),
                "last_active_at": datetime.utcnow()
            }}
        )
    
    return {"status": "success", "message": "Profile updated."}

@router.post("/user/survey")
async def update_survey(survey: SurveyResult):
    user_id = survey.userId
    db = await get_database()
    
    # userId 필드를 제외한 데이터 필터링
    survey_data = survey.dict(exclude={"userId"})
    
    # 1. 회원 정보 업데이트 시도
    result = await db["users"].update_one(
        {"id": user_id},
        {"$set": {"survey_data": survey_data, "last_updated": datetime.utcnow()}}
    )
    
    # 2. 회원이 없으면 게스트 컬렉션 업데이트
    if result.matched_count == 0:
        await db["guests"].update_one(
            {"id": user_id},
            {"$set": {
                "survey_data": survey_data, 
                "last_active_at": datetime.utcnow()
            }},
            upsert=True
        )
        print(f"✅ [Survey Guest] ID: {user_id}")
    else:
        print(f"✅ [Survey Member] ID: {user_id}")
        
    return {"status": "success", "message": "Survey data updated."}

@router.get("/user/{user_id}")
async def get_user_profile(user_id: str):
    db = await get_database()
    
    # 1. 회원 선조회
    profile = await db["users"].find_one({"id": user_id}, {"_id": 0})
    if profile:
        return profile
        
    # 2. 게스트 조회
    profile = await db["guests"].find_one({"id": user_id}, {"_id": 0})
    if profile:
        # 활동 시간 갱신 (TTL 연장)
        await db["guests"].update_one({"id": user_id}, {"$set": {"last_active_at": datetime.utcnow()}})
        return profile
        
    raise HTTPException(status_code=404, detail="User not found")

