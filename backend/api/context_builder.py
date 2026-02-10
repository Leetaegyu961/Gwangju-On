"""
Personalization Context Builder
Agent 호출 전에 사용자의 개인화 데이터를 수집하고,
LLM으로 간결한 요약문을 생성하여 QueryPlannerNode에 전달합니다.
"""

import os
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI


async def build_personalization_context(db, user_id: str) -> str:
    """
    DB에서 사용자의 개인화 데이터를 수집하고,
    LLM으로 Agent가 참고할 수 있는 간결한 요약문을 생성합니다.

    수집 데이터:
    1. preference_weights (테마 가중치 - 테이스팅 노트/행동 학습 결과)
    2. 최근 테이스팅 노트 3건 (atmosphere, satisfaction)
    3. 최근 chat_history 마지막 4턴

    Args:
        db: MongoDB database instance
        user_id: 사용자 ID

    Returns:
        개인화 컨텍스트 요약문 (빈 문자열이면 데이터 없음)
    """
    if not user_id:
        return ""

    # 1. 선호도 프로필 (preference_weights.themes)
    weights = {}
    try:
        pref = await db["user_preferences"].find_one({"userId": user_id})
        if pref:
            weights = pref.get("preference_weights", {}).get("themes", {})
    except Exception:
        pass

    # 2. 최근 테이스팅 노트 (최대 3건)
    recent_notes = []
    try:
        cursor = db["tasting_notes"].find({}).sort("created_at", -1).limit(20)
        all_notes = await cursor.to_list(20)
        # userId로 필터링 (tasting_notes에 userId가 직접 없을 수 있으므로 sessionId 기반)
        user_sessions = await db["user_trip_sessions"].find(
            {"userId": user_id}
        ).to_list(100)
        user_session_ids = {s.get("sessionId") for s in user_sessions if s.get("sessionId")}

        for note in all_notes:
            if note.get("sessionId") in user_session_ids:
                recent_notes.append(note)
            if len(recent_notes) >= 3:
                break
    except Exception:
        pass

    # 3. 최근 대화 히스토리 (현재 세션의 마지막 4턴)
    chat_history = []
    try:
        session = await db["user_trip_sessions"].find_one(
            {"userId": user_id, "status": {"$in": ["IN_PROGRESS", "COMPLETED"]}},
            sort=[("last_activity_at", -1)]
        )
        if session:
            intent_ctx = session.get("intent_context", {})
            if isinstance(intent_ctx, dict):
                chat_history = intent_ctx.get("chat_history", [])[-4:]
    except Exception:
        pass

    # 4. 데이터가 전혀 없으면 LLM 호출 스킵
    if not weights and not recent_notes and not chat_history:
        return ""

    # 5. Raw 데이터 조합
    parts = []

    if weights:
        # 가중치 상위 5개만 추출 (너무 많으면 불필요)
        top_weights = dict(sorted(weights.items(), key=lambda x: x[1], reverse=True)[:5])
        parts.append(f"선호 태그 가중치 (상위): {top_weights}")

    if recent_notes:
        note_summaries = []
        for n in recent_notes:
            raw = n.get("raw_response", {})
            note_summaries.append({
                "satisfaction": n.get("satisfaction"),
                "atmosphere": n.get("atmosphere"),
                "best_place": raw.get("best_place", ""),
            })
        parts.append(f"최근 여행 후기: {note_summaries}")

    if chat_history:
        chat_summary = [
            {"role": m.get("role", ""), "content": m.get("content", "")[:80]}
            for m in chat_history
        ]
        parts.append(f"최근 대화: {chat_summary}")

    raw_context = "\n".join(parts)

    # 6. LLM으로 요약 생성
    try:
        api_key = os.getenv("GOOGLE_API_KEY", "")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        if not api_key:
            # LLM 없이 raw 데이터를 간단히 정리하여 반환
            return _fallback_summary(weights, recent_notes, chat_history)

        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
        )

        prompt = f"""다음은 한 사용자의 여행 이력 데이터입니다.
코스 추천 AI가 참고할 수 있도록 핵심만 3문장 이내로 요약하세요.

포함할 내용:
- 선호하는 테마/분위기 (가중치가 높은 것 중심)
- 이전 여행에서 만족/불만족했던 점 (있다면)
- 최근 대화에서 요청한 내용 (있다면)

데이터가 부족하면 있는 것만 요약하세요. 없는 항목은 추측하지 마세요.

{raw_context}"""

        response = await llm.ainvoke(prompt)
        summary = response.content.strip()
        print(f"🧠 [Context Builder] Generated summary for {user_id}: {summary[:80]}...")
        return summary

    except Exception as e:
        print(f"⚠️ [Context Builder] LLM summary failed: {e}")
        return _fallback_summary(weights, recent_notes, chat_history)


def _fallback_summary(weights: dict, notes: list, history: list) -> str:
    """LLM 호출 실패 시 단순 텍스트 요약 생성"""
    parts = []
    if weights:
        top_tags = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
        tag_str = ", ".join(f"{t}({v:.1f})" for t, v in top_tags)
        parts.append(f"선호 테마: {tag_str}")
    if notes:
        avg_sat = sum(n.get("satisfaction", 3) for n in notes) / len(notes)
        parts.append(f"평균 만족도: {avg_sat:.1f}/5")
    return ". ".join(parts) if parts else ""
