"""
Refine Agent API Endpoint
src/refine_agent 패키지의 의도 분석 + 코스 수정 로직을 호출합니다.
"""

from typing import Optional, List, Dict
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from backend.db import get_database

router = APIRouter()


class RefineRequest(BaseModel):
    userId: str
    message: str
    courseIndex: int = 0


class RefineResponse(BaseModel):
    success: bool
    message: str
    courses: Optional[List[Dict]] = None
    changeSummary: Optional[str] = None


@router.post("/chat/refine", response_model=RefineResponse)
async def refine_course(request: RefineRequest):
    """코스 수정 요청을 처리합니다. (2~3초 응답)"""
    db = await get_database()

    # 1. Refinement Pool 로드
    ref_session = await db["refinement_sessions"].find_one({"userId": request.userId})
    if not ref_session:
        return RefineResponse(success=False, message="수정할 코스가 없어요. 먼저 코스를 생성해 주세요.")

    pool = ref_session.get("refinement_pool", [])
    current_courses = ref_session.get("current_courses", [])

    if not current_courses:
        return RefineResponse(success=False, message="저장된 코스가 없어요.")

    # 2. Refine Agent 호출 (src/refine_agent)
    from src.refine_agent import analyze_refinement_intent, apply_modification

    intent = await analyze_refinement_intent(request.message, current_courses, request.courseIndex)
    modified_courses, change_summary = apply_modification(current_courses, pool, intent)

    # 3. DB 업데이트
    await db["refinement_sessions"].update_one(
        {"userId": request.userId},
        {"$set": {"current_courses": modified_courses, "last_refined_at": datetime.now().isoformat()}}
    )

    # 4. 수정 로그
    await db["refinement_logs"].insert_one({
        "userId": request.userId,
        "message": request.message,
        "intent": intent.model_dump(),
        "change_summary": change_summary,
        "timestamp": datetime.now().isoformat()
    })

    print(f"✅ [RefineAgent] {change_summary}")

    return RefineResponse(success=True, message=change_summary, courses=modified_courses, changeSummary=change_summary)
