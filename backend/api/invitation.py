from fastapi import APIRouter, HTTPException, Depends
from backend.db import get_database
from backend.models.user import UserAccount, CoursePoint
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from src.agent.graph import app as agent_app
import json
import re
import uuid

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
