from fastapi import APIRouter, HTTPException, Depends
from backend.db import get_database
from backend.models.user import UserAccount, CoursePoint
from backend.api.context_builder import build_personalization_context
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from src.agent.graph import app as agent_app
from datetime import datetime, timedelta
import json
import re
import uuid
import random

router = APIRouter()

@router.get("/invitation/ping")
async def ping_invitation():
    return {"message": "Invitation router is working"}

class InvitationResponse(BaseModel):
    has_seen: bool

@router.patch("/invitation/seen/{user_id}")
async def mark_invitation_seen(user_id: str):
    db = await get_database()
    result = await db["users"].update_one(
        {"id": user_id},
        {"$set": {"has_seen_invitation": True}}
    )
    if result.modified_count == 0:
        user = await db["users"].find_one({"id": user_id})
        if not user:
             raise HTTPException(status_code=404, detail="User not found")
        
    return {"status": "success", "message": "Invitation marked as seen."}

class InvitationCourseCard(BaseModel):
    course_id: int
    title: str
    description: str
    places: list[CoursePoint]

@router.get("/invitation/generate/{user_id}")
async def generate_invitation_courses(user_id: str):
    db = await get_database()
    
    # 1. Fetch User Data
    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Prepare Context from Survey
    # Since we minimize DB changes, we rely on 'survey_data' if available, or fetch from existing session?
    # Usually guest/new user might not have a session yet if they just logged in.
    # But for 'invitation', we assume they have some onboarding data.
    # If they are a fresh user without survey, we might need default hot places.
    
    # Check if user has survey data in 'users' collection (from onboard/survey API)
    # The 'users' collection Google User might not have 'survey_data' directly if it's stored in 'user_trip_sessions'.
    # Let's check 'user_trip_sessions' for the latest session.
    session_doc = await db["user_trip_sessions"].find_one(
        {"userId": user_id},
        sort=[("created_at", -1)]
    )
    
    survey_data = {}
    if session_doc:
        intent_ctx = session_doc.get("intent_context", {})
        survey_data = intent_ctx.get("survey_data", {})
    
    # If no survey data, we can't really generate personalized courses.
    # We'll try to use whatever we have or ask for "Gwangju Hot Places" as generic.
    
    prompt = f"""
    [SYSTEM: SPECIAL INSTRUCTION FOR INVITATION]
    You are generating a 'Welcome Invitation' for a returning or new user.
    Generate EXACTLY 3 distinct course concepts for Gwangju travel.
    
    1. Concept 1 (Comfortable): Safe, popular, rated high.
    2. Concept 2 (New): Unique, hidden gems, slightly away from main spots.
    3. Concept 3 (Trendy): Instagrammable, hot places, recent trends.
    
    Each course MUST have 4 places.
    Return the result in the standard JSON format used for course recommendations.
    Keys: recommended_courses (list of 3 objects), each having course_id, course_name, course_description, places.
    Each place: id, name, type, reason.
    
    User Context (Survey): {survey_data}
    """
    
    try:
        # 3. Invoke Agent
        result = await agent_app.ainvoke({
            "messages": [HumanMessage(content=prompt)],
            "survey_data": survey_data # Pass it if defined in graph state
        })
        
        # 4. Parse Result (Reusing logic from chat.py roughly)
        final_answer_raw = result.get("final_answer", "")
        if isinstance(final_answer_raw, list):
             final_answer_raw = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in final_answer_raw])
        
        final_answer_raw = str(final_answer_raw)
        
        # JSON Cleaning
        clean_json = final_answer_raw.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)
            
        parsed_output = json.loads(clean_json)
        courses_data = parsed_output.get("recommended_courses", [])
        
        # Fallback if structure differs
        if not courses_data and "courses" in parsed_output:
             courses_data = parsed_output["courses"]
             
        final_courses = []
        for idx, c in enumerate(courses_data):
            # Create Card
            p_list = []
            for p in c.get("places", []):
                # Simple mapping
                p_list.append(CoursePoint(
                    id=str(p.get("id", uuid.uuid4())), 
                    type=p.get("type", "Place"),
                    name=p.get("name", "Unknown"),
                    desc=p.get("reason", "Good place"),
                    img=None # Image mapping requires complex logic, omitted for MVP speed or add basic if needed
                ))
            
            final_courses.append(InvitationCourseCard(
                course_id=c.get("course_id", idx+1),
                title=c.get("course_name", f"Course {idx+1}"),
                description=c.get("course_description", "Enjoy Gwangju!"),
                places=p_list
            ))
            
        return final_courses

    except Exception as e:
        print(f"Error generating invitation: {e}")
        # Return empty list or default static fallback
        return []


# ─── Personalized Invitation Endpoints ───

PERSONALIZED_INVITATION_TTL_HOURS = 24


@router.get("/invitation/personalized/{user_id}")
async def get_personalized_invitation(user_id: str):
    """
    개인화 초대장을 조회/생성합니다.
    - 미열람 레코드가 있으면 그대로 반환
    - 열람 후 24시간 이상 경과하면 새로 생성
    - 열람 후 24시간 미만이면 null 반환 (프론트엔드에서 하드코딩 사용)
    - 사용자 데이터가 없으면 null 반환
    """
    db = await get_database()

    # 1. 기존 개인화 초대장 조회
    record = await db["personalized_invitations"].find_one({"userId": user_id})

    if record:
        viewed_at = record.get("viewed_at")

        # 아직 안 본 초대장이 있으면 그대로 반환
        if viewed_at is None:
            invitation = record.get("invitation", {})
            if "_id" in invitation:
                invitation.pop("_id")
            return {"invitation": invitation}

        # 본 지 24시간 미만이면 null 반환
        viewed_dt = datetime.fromisoformat(viewed_at) if isinstance(viewed_at, str) else viewed_at
        if datetime.now() - viewed_dt < timedelta(hours=PERSONALIZED_INVITATION_TTL_HOURS):
            return {"invitation": None}

    # 2. 새로 생성 필요: 사용자 컨텍스트 수집
    personalization_summary = await build_personalization_context(db, user_id)

    if not personalization_summary:
        return {"invitation": None}

    # 3. Agent 파이프라인으로 코스 생성
    try:
        # 사용자 세션에서 survey_data 가져오기
        session_doc = await db["user_trip_sessions"].find_one(
            {"userId": user_id},
            sort=[("created_at", -1)]
        )
        survey_data = {}
        if session_doc:
            intent_ctx = session_doc.get("intent_context", {})
            survey_data = intent_ctx.get("survey_data", {})

        prompt = f"""
        [SYSTEM: PERSONALIZED INVITATION]
        You are generating a personalized travel invitation based on the user's history and preferences.

        사용자 컨텍스트: {personalization_summary}

        이 사용자의 취향에 맞는 광주 여행 코스 1개를 생성하세요.
        코스에는 4개 장소를 포함하세요.

        Return the result in JSON format.
        Keys: recommended_courses (list of 1 object), each having course_id, course_name, course_description, places.
        Each place: id, name, type, lat, lng, reason.

        User Survey Data: {survey_data}
        """

        result = await agent_app.ainvoke({
            "messages": [HumanMessage(content=prompt)],
            "survey_data": survey_data,
            "personalization_context": personalization_summary,
            "userId": user_id,
        })

        # 4. 결과 파싱
        final_answer_raw = result.get("final_answer", "")
        if isinstance(final_answer_raw, list):
            final_answer_raw = "".join([
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in final_answer_raw
            ])

        final_answer_raw = str(final_answer_raw)

        clean_json = final_answer_raw.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)

        parsed_output = json.loads(clean_json)
        courses_data = parsed_output.get("recommended_courses", [])

        if not courses_data and "courses" in parsed_output:
            courses_data = parsed_output["courses"]

        if not courses_data:
            print(f"⚠️ [Personalized Invitation] No courses generated for {user_id}")
            return {"invitation": None}

        # Agent가 3개 코스를 생성하면 랜덤으로 1개 선택
        selected_course = random.choice(courses_data)

        # 5. 초대장 형식으로 변환
        places = []
        for p in selected_course.get("places", []):
            places.append({
                "id": str(p.get("id", str(uuid.uuid4()))),
                "name": p.get("name", "Unknown"),
                "type": p.get("type", "장소"),
                "lat": p.get("lat"),
                "lng": p.get("lng"),
                "desc": p.get("reason", p.get("desc", "추천 장소")),
                "img": None,
            })

        invitation_id = f"personalized-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        invitation = {
            "id": invitation_id,
            "course_id": 99,
            "title": selected_course.get("course_name", "당신을 위한 맞춤 코스"),
            "description": selected_course.get("course_description", "취향을 분석해 만든 특별한 여행 코스입니다."),
            "places": places,
        }

        # 6. DB에 저장 (upsert)
        await db["personalized_invitations"].update_one(
            {"userId": user_id},
            {"$set": {
                "userId": user_id,
                "invitation": invitation,
                "created_at": datetime.now().isoformat(),
                "viewed_at": None,
            }},
            upsert=True
        )

        print(f"✨ [Personalized Invitation] Generated for {user_id}: {invitation['title']}")
        return {"invitation": invitation}

    except Exception as e:
        print(f"❌ [Personalized Invitation] Generation failed for {user_id}: {e}")
        return {"invitation": None}


@router.patch("/invitation/personalized/viewed/{user_id}")
async def mark_personalized_invitation_viewed(user_id: str):
    """
    개인화 초대장을 열람 처리합니다.
    viewed_at이 null인 경우에만 현재 시각으로 업데이트합니다.
    """
    db = await get_database()

    result = await db["personalized_invitations"].update_one(
        {"userId": user_id, "viewed_at": None},
        {"$set": {"viewed_at": datetime.now().isoformat()}}
    )

    if result.modified_count == 0:
        # 이미 viewed이거나 레코드 없음
        return {"status": "no_change", "message": "Already viewed or not found"}

    return {"status": "success", "message": "Personalized invitation marked as viewed"}
