from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.course import Course, TravelLog, PlaceMetadata
from backend.db import get_database
from typing import List
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import json

router = APIRouter()

async def generate_course_summary(course_id: str):
    """
    Background Task: Gemini를 사용하여 코스의 제목과 요약문을 생성합니다.
    """
    db = await get_database()
    course_data = await db["courses"].find_one({"id": course_id})
    if not course_data:
        return

    places_str = ", ".join([p["name"] for p in course_data["places"]])
    
    prompt = f"""
    다음 여행지 코스에 대해 매력적인 제목과 1~2문장의 감성적인 요약문을 만들어줘.
    장소들: {places_str}
    
    형식: JSON
    {{ "title": "제목", "summary": "요약문" }}
    """
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GOOGLE_MAPS_API_KEY")) # API Key 공유 가능성 고려
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # JSON 추출
        content = response.content.strip()
        if content.startswith("```"):
            import re
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            
        data = json.loads(content)
        
        await db["courses"].update_one(
            {"id": course_id},
            {"$set": {
                "title": data.get("title", course_data["title"]),
                "summary_text": data.get("summary", "")
            }}
        )
        print(f"✨ [AI Summary] Generated for Course: {course_id}")
    except Exception as e:
        print(f"❌ [AI Summary Error] {e}")

@router.post("/course/save")
async def save_course(course: Course, background_tasks: BackgroundTasks):
    db = await get_database()
    
    # 1. 저장
    await db["courses"].insert_one(course.dict())
    
    # 2. 유저의 saved_course_ids 업데이트
    await db["users"].update_one(
        {"id": course.owner_id},
        {"$addToSet": {"saved_course_ids": course.id}}
    )
    
    # 3. 백그라운드에서 AI 요약 생성
    background_tasks.add_task(generate_course_summary, course.id)
    
    return {"status": "success", "course_id": course.id}

@router.get("/user/saved-courses", response_model=List[Course])
async def get_saved_courses(userId: str):
    db = await get_database()
    
    # 유저의 저장된 ID 리스트 확인
    user = await db["users"].find_one({"id": userId})
    if not user:
        # 게스트에서도 조회
        user = await db["guests"].find_one({"id": userId})
        
    if not user or "saved_course_ids" not in user:
        return []
        
    # 실제 코스 데이터 조회
    list_courses = await db["courses"].find({"id": {"$in": user["saved_course_ids"]}}).to_list(100)
    # _id 제거 (Pydantic 모델 호환)
    for c in list_courses:
        c.pop("_id", None)
        
    return list_courses

@router.post("/user/travel-log")
async def save_travel_log(log: TravelLog):
    db = await get_database()
    
    # 1. 저장
    await db["travel_logs"].insert_one(log.dict())
    
    # 2. 유저의 travel_log_ids 업데이트
    await db["users"].update_one(
        {"id": log.owner_id},
        {"$addToSet": {"travel_log_ids": log.id}}
    )
    
    return {"status": "success", "log_id": log.id}

@router.get("/course/share/{share_id}", response_model=Course)
async def get_shared_course(share_id: str):
    db = await get_database()
    course = await db["courses"].find_one({"share_id": share_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Shared course not found")
    return course
