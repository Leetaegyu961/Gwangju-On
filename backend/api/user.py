from fastapi import APIRouter
from pydantic import BaseModel
from backend.models.user import UserProfile, OnboardingResponse, SurveyResult, UserPreferenceProfile, DetailedInteractionLog
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

    # 5. [New] UserPreferenceProfile 업데이트 (설문 기반 초기 선호도 설정)
    try:
        existing_pref = await db["user_preferences"].find_one({"userId": user_id})
        
        # 기존 가중치 로드
        current_weights = {}
        if existing_pref and "preference_weights" in existing_pref:
            current_weights = existing_pref["preference_weights"].get("themes", {})
        
        # 설문에서 선택된 테마에 가중치 부여 (+1.0)
        # 상한 5.0 적용하여 편향 방지 (반복 설문으로 무한 증가 방지)
        for theme in survey.themes:
            current_val = current_weights.get(theme, 0.0) + 1.0
            current_weights[theme] = min(5.0, current_val)
            
        # 예산 민감도 추정 (예산이 낮으면 민감도 높음)
        # budget: [min, max] (단위: 만원)
        avg_budget = sum(survey.budget) / 2
        price_sensitivity = 0.8 if avg_budget < 10 else (0.5 if avg_budget < 30 else 0.2)

        pref_update = {
            "userId": user_id,
            "last_updated": datetime.now().isoformat(),
            "preference_weights": {
                "themes": current_weights,
                "price_sensitivity": price_sensitivity
            }
        }
        
        await db["user_preferences"].update_one(
            {"userId": user_id},
            {"$set": pref_update},
            upsert=True
        )
        print(f"✅ [API] User Preference Updated for {user_id}")
        
    except Exception as e:
        print(f"⚠️ [API] Failed to update user preference: {e}")
        
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

class UpdateProfileRequest(BaseModel):
    userId: str
    age: str
    gender: str

@router.put("/user/profile")
async def update_user_profile(req: UpdateProfileRequest):
    """
    Updates the user's demographic information (Age/Gender).
    """
    db = await get_database()
    
    # 1. Update In-Memory (Guest/Cache)
    if req.userId in USER_DB:
        USER_DB[req.userId].update({"age": req.age, "gender": req.gender})
    
    # 2. Update MongoDB (User)
    result = await db["users"].update_one(
        {"id": req.userId},
        {"$set": {"age": req.age, "gender": req.gender}}
    )
    
    return {"status": "success", "message": "Profile updated"}

# --- User Preference APIs ---

@router.get("/user/{user_id}/preference")
async def get_user_preference(user_id: str):
    db = await get_database()
    profile = await db["user_preferences"].find_one({"userId": user_id})
    if profile:
        profile.pop("_id", None)
        return profile
    return {"message": "No preference profile found", "userId": user_id}

@router.post("/user/preference")
async def update_user_preference(profile: UserPreferenceProfile):
    db = await get_database()
    await db["user_preferences"].update_one(
        {"userId": profile.userId},
        {"$set": profile.dict()},
        upsert=True
    )
    return {"status": "success", "message": "Preference updated"}

@router.post("/user/log-interaction")
async def log_interaction(log: DetailedInteractionLog):
    db = await get_database()
    await db["detailed_interaction_logs"].insert_one(log.dict())
    
    # Optional: Trigger async preference update here based on interaction
    # For now, we just log it.
    
    return {"status": "success", "message": "Interaction logged"}

@router.get("/user/{user_id}/statistics")
async def get_user_statistics(user_id: str):
    """
    사용자 선호도 및 통계 정보 반환 (마이페이지 시각화용)
    """
    db = await get_database()
    
    # 1. Fetch Preferences
    pref = await db["user_preferences"].find_one({"userId": user_id})
    
    # 기본값 설정
    weights = {}
    price_sensitivity = 0.5
    last_updated = None
    
    if pref:
        weights = pref.get("preference_weights", {}).get("themes", {})
        price_sensitivity = pref.get("preference_weights", {}).get("price_sensitivity", 0.5)
        last_updated = pref.get("last_updated")
    
    # Sort themes by weight (Top 5)
    top_themes = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # 2. Fetch Session History (Budget Stats)
    cursor = db["user_trip_sessions"].find({"userId": user_id})
    total_budget = 0
    session_count = 0
    
    async for session in cursor:
        # intent_context -> survey_data -> budget
        intent = session.get("intent_context", {})
        if isinstance(intent, dict):
             survey = intent.get("survey_data", {})
             if isinstance(survey, dict):
                budget_range = survey.get("budget", [])
                if budget_range and isinstance(budget_range, list) and len(budget_range) >= 2:
                    # [min, max] 평균값 사용
                    avg_session_budget = (budget_range[0] + budget_range[1]) / 2
                    total_budget += avg_session_budget
                    session_count += 1
            
    avg_budget = round(total_budget / session_count, 1) if session_count > 0 else 0
    
    return {
        "userId": user_id,
        "top_themes": [{"theme": t, "score": round(w, 2)} for t, w in top_themes],
        "price_sensitivity_score": price_sensitivity, # 0.0 ~ 1.0 (높을수록 민감)
        "price_sensitivity_label": "High" if price_sensitivity >= 0.7 else ("Medium" if price_sensitivity >= 0.4 else "Low"),
        "average_budget": avg_budget, # 단위: 만원
        "total_trips": session_count,
        "last_updated": last_updated
    }

@router.get("/user/{user_id}/agent-context")
async def get_agent_context(user_id: str):
    """
    에이전트가 사용 중인 모든 컨텍스트 정보 반환 (대시보드용)
    """
    db = await get_database()
    
    # 1. User Preference Profile (장기 기억)
    profile = await db["user_preferences"].find_one({"userId": user_id})
    if profile: profile.pop("_id", None)
    
    # 2. Active Session (단기 기억: 의도, 설문, 채팅 히스토리)
    # 가장 최근 세션 조회
    session = await db["user_trip_sessions"].find_one(
        {"userId": user_id},
        sort=[("last_activity_at", -1)]
    )
    if session: session.pop("_id", None)
    
    # 3. Recent Interaction Logs (행동 로그)
    logs_cursor = db["detailed_interaction_logs"].find({"userId": user_id}).sort("timestamp", -1).limit(10)
    logs = []
    async for log in logs_cursor:
        log.pop("_id", None)
        logs.append(log)
        
    return {
        "userId": user_id,
        "profile": profile,
        "active_session": session,
        "recent_logs": logs
    }