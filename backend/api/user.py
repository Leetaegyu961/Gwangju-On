from fastapi import APIRouter
from backend.models.user import UserProfile, OnboardingResponse, SurveyResult
import uuid

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
    if user_id in USER_DB:
        # 기존 프로필 정보에 설문 정보 합치기
        USER_DB[user_id].update(survey.dict(exclude={"userId"}))
        print(f"✅ [Survey Update] ID: {user_id}, Data: {USER_DB[user_id]}")
        return {"status": "success", "message": "Survey data updated."}
    else:
        # 혹시 ID가 없으면 새로 생성해서 저장 (예외 처리)
        USER_DB[user_id] = survey.dict(exclude={"userId"})
        print(f"⚠️ [Survey New] ID: {user_id} (Not found in onboard), Data: {USER_DB[user_id]}")
        return {"status": "success", "message": "Survey data saved (new session)."}

# (옵션) 저장된 정보 확인용 API
@router.get("/user/{user_id}")
async def get_user_profile(user_id: str):
    profile = USER_DB.get(user_id)
    if profile:
        return profile
    return {"error": "User not found"}
