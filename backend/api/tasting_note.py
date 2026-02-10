from fastapi import APIRouter, HTTPException
from backend.db import get_database
from backend.models.user import TastingNoteEntry
from backend.api.preference_utils import learn_from_tasting_note
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/user/session/tasting-notes")
async def save_tasting_note(user_id: str, note: dict):
    db = await get_database()
    
    # Find active session to get sessionId
    session = await db["user_trip_sessions"].find_one({"userId": user_id})
    session_id = session.get("sessionId") if session else "unknown"
    
    note_entry = TastingNoteEntry(
        sessionId=session_id,
        satisfaction=note.get("satisfaction", 0),
        atmosphere=str(note.get("atmosphere", "")),
        movement=str(note.get("movement", "")),
        best_place_id=str(note.get("best_place", "")), # frontend sends best_place
        ai_quality=str(note.get("card_choice_style", "")), # frontend sends card_choice_style
        raw_response=note,
        created_at=datetime.now().isoformat()
    )
    
    # 1. tasting_notes 별도 컬렉션에 저장
    await db["tasting_notes"].insert_one(note_entry.dict())
    
    # 2. 세션 상태 완료 및 last_activity_at 업데이트
    await db["user_trip_sessions"].update_one(
        {"userId": user_id},
        {"$set": {
            "status": "COMPLETED",
            "last_activity_at": datetime.now().isoformat()
        }}
    )

    # 3. [Preference Learning] 만족도 기반 선호도 점진 학습
    try:
        satisfaction = note.get("satisfaction", 3)
        session_themes = []
        if session:
            intent_ctx = session.get("intent_context", {})
            if isinstance(intent_ctx, dict):
                survey = intent_ctx.get("survey_data", {})
                if isinstance(survey, dict):
                    session_themes = survey.get("themes", [])
        await learn_from_tasting_note(
            db, user_id, satisfaction, session_themes,
            atmosphere=note.get("atmosphere"),
            best_place_id=note.get("best_place")
        )
    except Exception as e:
        print(f"⚠️ [Preference Learning] tasting-note failed: {e}")

    return {"status": "success", "message": "Tasting note saved and session completed"}
