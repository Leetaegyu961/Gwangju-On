from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.models.chat import ChatRequest, ChatResponse, EvidenceCard, ValidateRequest, ValidateResponse
from datetime import datetime
import time
import uuid
import json
import asyncio
from backend.db import get_database
from backend.api.context_builder import build_personalization_context
import os

router = APIRouter()


# ─────────────────────────────────────────────
# Intent Classification (에이전트 실행 전 분류)
# ─────────────────────────────────────────────

async def classify_intent(message: str) -> str:
    """
    사용자 메시지를 분석하여 'course' 또는 'general'로 분류합니다.
    - course: 코스/투어/경로 생성 요청
    - general: 장소 리스트, 단일 추천, 맛집 검색 등 나머지
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from pydantic import BaseModel, Field

    class IntentResult(BaseModel):
        intent: str = Field(description="'course' 또는 'general'")

    try:
        google_api_key = os.getenv("GOOGLE_API_KEY", "")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        llm = ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=google_api_key,
            temperature=0,
        )
        structured_llm = llm.with_structured_output(IntentResult)

        prompt = f"""사용자 메시지의 의도를 분류하세요.

- "course": 반드시 "코스", "투어", "일정" 등의 **키워드가 명시적으로 포함**된 경우만 해당
  키워드: "코스", "코스 짜줘", "코스 추천", "투어", "하루 일정", "반나절", "코스 만들어줘", "코스 생성", "바로 코스 생성하기"
  예: "동명동 데이트 코스", "카페 투어 코스 짜줘", "가족여행 코스"

- "general": 위 키워드가 없는 모든 요청. 장소 리스트, 단일 추천, 맛집 검색, 조건 검색, 순서 지정 등 전부 포함.
  예: "동명동 카페 리스트", "점심 뭐 먹지?", "떡갈비 맛집", "고깃집 5개 추천"
  **주의**: "첫 번째는 한식집, 두 번째는 카페"처럼 순서를 지정하더라도 "코스"라는 단어가 없으면 general입니다.
  **주의**: "점심은 국밥, 저녁은 이탈리안"처럼 시간대별 추천도 "코스"가 없으면 general입니다.

사용자 메시지: "{message}"
"""
        result = await structured_llm.ainvoke(prompt)
        if result and result.intent in ("course", "general"):
            print(f"🎯 [Intent] '{message}' → {result.intent}")
            return result.intent
    except Exception as e:
        print(f"⚠️ [Intent] Classification failed: {e}")

    # 기본값: course (기존 동작 유지)
    print(f"🎯 [Intent] '{message}' → course (default)")
    return "course"


# ─────────────────────────────────────────────
# SSE Streaming Endpoint
# ─────────────────────────────────────────────

NODE_PROGRESS = {
    "query_planner_node": {"step": "planning", "message": "여행 테마를 분석하고 있어요...", "progress": 10, "icon": "search"},
    "vector_retrieval_node": {"step": "searching", "message": "AI 데이터베이스를 검색 중이에요...", "progress": 25, "icon": "database"},
    "keyword_retrieval_node": {"step": "searching", "message": "맛집 정보를 수집하고 있어요...", "progress": 30, "icon": "map"},
    "enrichment_node": {"step": "enriching", "message": "장소 상세 정보를 조회하고 있어요...", "progress": 50, "icon": "info"},
    "naver_blog_search_node": {"step": "reviewing", "message": "블로그 리뷰를 분석하고 있어요...", "progress": 60, "icon": "review"},
    "scoring_node": {"step": "scoring", "message": "점수를 매기고 최적 코스를 계산해요...", "progress": 75, "icon": "star"},
    "generate_course_1": {"step": "generating", "message": "맞춤 코스를 만들고 있어요...", "progress": 85, "icon": "sparkle"},
    "aggregator_node": {"step": "finalizing", "message": "최종 결과를 정리하고 있어요...", "progress": 95, "icon": "check"},
    # General Agent 노드 진행 상황
    "query_analyzer": {"step": "planning", "message": "질문을 분석하고 있어요...", "progress": 15, "icon": "search"},
    "search_node": {"step": "searching", "message": "장소를 검색하고 있어요...", "progress": 40, "icon": "map"},
    "enrichment_node": {"step": "enriching", "message": "장소 상세 정보를 조회하고 있어요...", "progress": 65, "icon": "info"},
    "response_node": {"step": "generating", "message": "추천 장소를 정리하고 있어요...", "progress": 90, "icon": "sparkle"},
}

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    input_text = request.message
    user_id = request.userId

    db = await get_database()
    session_doc = await db["user_trip_sessions"].find_one({"userId": user_id})

    survey_data = {}
    if session_doc:
        intent_ctx = session_doc.get("intent_context", {})
        survey_data = intent_ctx.get("survey_data", {})

        chat_msg = {"role": "user", "content": input_text, "timestamp": datetime.now().isoformat()}
        await db["user_trip_sessions"].update_one(
            {"userId": user_id},
            {
                "$push": {"intent_context.chat_history": chat_msg},
                "$set": {"last_activity_at": datetime.now().isoformat()}
            }
        )

    # Intent 분류 (에이전트 실행 전)
    intent = await classify_intent(input_text)

    # 개인화 컨텍스트 (course 에이전트에서만 사용)
    personalization_ctx = ""
    if intent == "course":
        try:
            personalization_ctx = await build_personalization_context(db, user_id)
        except Exception as e:
            print(f"⚠️ [Context Builder] Failed: {e}")

    async def event_generator():
        from langchain_core.messages import HumanMessage

        sent_steps = set()

        try:
            if intent == "general":
                # General Agent 사용 (서베이/개인화 없음)
                from src.general_agent.graph import app as general_app

                initial_state = {
                    "messages": [HumanMessage(content=input_text)],
                }

                async for event in general_app.astream_events(initial_state, version="v2"):
                    event_type = event.get("event", "")
                    node_name = event.get("name", "")

                    if event_type == "on_chain_start" and node_name in NODE_PROGRESS:
                        if node_name not in sent_steps:
                            sent_steps.add(node_name)
                            progress = NODE_PROGRESS[node_name]
                            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

                    if event_type == "on_chain_end" and node_name == "LangGraph":
                        output = event.get("data", {}).get("output", {})
                        final_result = _build_chat_response(output, user_id)
                        yield f"data: {json.dumps({'step': 'done', 'progress': 100, 'result': final_result}, ensure_ascii=False)}\n\n"
                        await _save_chat_result(db, user_id, input_text, final_result)

            else:
                # Course Agent 사용 (기존 메인 에이전트)
                from src.agent.graph import app as agent_app

                initial_state = {
                    "messages": [HumanMessage(content=input_text)],
                    "survey_data": survey_data,
                    "userId": user_id,
                    "personalization_context": personalization_ctx
                }

                async for event in agent_app.astream_events(initial_state, version="v2"):
                    event_type = event.get("event", "")
                    node_name = event.get("name", "")

                    if event_type == "on_chain_start" and node_name in NODE_PROGRESS:
                        if node_name not in sent_steps:
                            sent_steps.add(node_name)
                            progress = NODE_PROGRESS[node_name]
                            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

                    if event_type == "on_chain_end" and node_name == "LangGraph":
                        output = event.get("data", {}).get("output", {})
                        final_result = _build_chat_response(output, user_id)
                        yield f"data: {json.dumps({'step': 'done', 'progress': 100, 'result': final_result}, ensure_ascii=False)}\n\n"
                        await _save_chat_result(db, user_id, input_text, final_result)
                        await _save_refinement_pool(db, user_id, output)

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_result = {
                "step": "error",
                "progress": 0,
                "result": {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "text": "죄송해요, 여행 정보를 찾는 중에 문제가 발생했어요. 잠시 후 다시 시도해 주세요.",
                    "isDecisionPoint": False,
                    "status": "done"
                }
            }
            yield f"data: {json.dumps(error_result, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _build_chat_response(agent_output: dict, user_id: str) -> dict:
    """Agent 출력을 ChatResponse 형식의 dict로 변환합니다."""
    import re

    final_answer_raw = agent_output.get("final_answer", "")
    if isinstance(final_answer_raw, list):
        final_answer_raw = "".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in final_answer_raw])
    final_answer_raw = str(final_answer_raw)

    enriched_results = agent_output.get("enriched_results", [])
    place_photo_map = {}

    def normalize_name(n):
        return n.replace(" ", "").lower() if n else ""

    # enriched_results에서 사진 + 좌표 매핑 (LLM 출력 보정용)
    place_detail_map = {}  # name -> {photo_name, lat, lng}
    if enriched_results:
        for item in enriched_results:
            p = item.get('place', {})
            p_name = p.get('name')
            if p_name:
                norm_key = normalize_name(p_name)
                place_detail_map[norm_key] = {
                    "photo_name": p.get('photo_name'),
                    "lat": p.get('lat'),
                    "lng": p.get('lng'),
                }
                if p.get('photo_name'):
                    place_photo_map[norm_key] = p['photo_name']

    try:
        clean_json = final_answer_raw.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)

        parsed_output = json.loads(clean_json)
        response_text = parsed_output.get("answer", final_answer_raw)
        recommended_courses = parsed_output.get("recommended_courses", [])

        if not recommended_courses:
            courses_data = parsed_output.get("courses", [])
            if courses_data:
                recommended_courses = [{"course_id": 1, "course_name": "추천 코스", "places": courses_data}]

        all_courses = []
        for course_idx, course in enumerate(recommended_courses):
            course_cards = []
            for idx, place in enumerate(course.get("places", [])):
                place_name = place.get("name", "")
                photo_name = place_photo_map.get(normalize_name(place_name))
                api_url = os.getenv("API_URL", "http://localhost:8000")
                img_url = f"{api_url}/api/photo?name={photo_name}" if photo_name else None

                # LLM이 좌표를 누락/부정확하게 출력한 경우 enriched_results에서 보정
                lat = place.get("lat")
                lng = place.get("lng")
                detail = place_detail_map.get(normalize_name(place_name), {})
                if (not lat or not lng or lat == 0 or lng == 0) and detail:
                    lat = detail.get("lat") or lat
                    lng = detail.get("lng") or lng

                course_cards.append({
                    "placeId": place.get("id") or f"p{idx}",
                    "name": place_name,
                    "reason": place.get("reason", "추천 장소"),
                    "reviewSummary": place.get("reason", "추천 장소"),
                    "risks": "",
                    "trustScore": 90,
                    "keywords": [place.get("type", "장소")],
                    "lat": lat,
                    "lng": lng,
                    "img": img_url,
                    "photo_name": photo_name
                })

            all_courses.append({
                "course_id": course.get("course_id", course_idx + 1),
                "course_name": course.get("course_name", f"코스 {course_idx + 1}"),
                "course_description": course.get("course_description", ""),
                "cards": course_cards
            })

        evidence_cards = all_courses[0]["cards"] if all_courses else []
        is_plan_request = bool(evidence_cards)

    except (json.JSONDecodeError, Exception):
        response_text = final_answer_raw
        evidence_cards = []
        all_courses = []
        is_plan_request = False

    return {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "text": response_text,
        "isDecisionPoint": is_plan_request,
        "evidenceCards": evidence_cards,
        "allCourses": all_courses if all_courses else None,
        "status": "done"
    }


async def _save_chat_result(db, user_id: str, input_text: str, result: dict):
    """채팅 결과를 DB에 저장합니다."""
    try:
        ai_msg = {"role": "assistant", "content": result.get("text", ""), "timestamp": datetime.now().isoformat()}
        update_fields = {"last_activity_at": datetime.now().isoformat()}
        if result.get("isDecisionPoint"):
            update_fields["status"] = "COMPLETED"

        await db["user_trip_sessions"].update_one(
            {"userId": user_id},
            {
                "$push": {"intent_context.chat_history": ai_msg},
                "$set": update_fields
            }
        )

        # Auto-save courses
        all_courses = result.get("allCourses")
        if result.get("isDecisionPoint") and all_courses:
            group_id = str(uuid.uuid4())
            ts = datetime.now().isoformat()
            for course in all_courses:
                points = [{"id": str(c.get("placeId", "")), "name": c.get("name", ""), "lat": c.get("lat", 0), "lng": c.get("lng", 0), "desc": c.get("reason", ""), "img": c.get("img"), "photo_name": c.get("photo_name"), "tags": c.get("keywords", []), "transport": "이동", "type": (c.get("keywords", [None]) or [None])[0]} for c in course.get("cards", [])]
                new_session = {"sessionId": str(uuid.uuid4()), "group_id": group_id, "userId": user_id, "status": "COMPLETED_CANDIDATE", "is_selected": False, "title": course.get("course_name", "추천 코스"), "course_description": course.get("course_description", ""), "album_data": points, "total_courses": len(points), "ai_summary": result.get("text", "")[:100], "created_at": ts, "completed_at": ts, "last_activity_at": ts, "intent_context": {"auto_saved": True}}
                await db["user_trip_sessions"].insert_one(new_session)
                course["course_id"] = new_session["sessionId"]
                course["group_id"] = group_id
    except Exception as e:
        print(f"⚠️ [SSE] Save failed: {e}")


async def _save_refinement_pool(db, user_id: str, agent_output: dict):
    """코스 수정용 후보 장소 풀을 DB에 저장합니다."""
    try:
        enriched = agent_output.get("enriched_results", [])
        courses = agent_output.get("generated_courses", [])

        if not enriched or not courses:
            return

        # 후보 풀: 각 장소의 핵심 정보만 저장 (용량 절약)
        pool = []
        for item in enriched:
            p = item.get("place", {})
            pool.append({
                "id": p.get("id", ""),
                "name": p.get("name", ""),
                "address": p.get("address", ""),
                "lat": p.get("lat", 0),
                "lng": p.get("lng", 0),
                "rating": p.get("rating", 0),
                "total_reviews": p.get("total_reviews", 0),
                "price_level": p.get("price_level", ""),
                "photo_name": p.get("photo_name"),
                "keywords": p.get("keywords", {}),
                "source": p.get("source", ""),
                "type": _infer_type_for_pool(p),
                "score": item.get("score", 0),
            })

        await db["refinement_sessions"].update_one(
            {"userId": user_id},
            {"$set": {
                "userId": user_id,
                "refinement_pool": pool,
                "current_courses": courses,
                "created_at": datetime.now().isoformat(),
            }},
            upsert=True
        )
        print(f"✅ [Refinement Pool] Saved {len(pool)} candidates for {user_id}")

    except Exception as e:
        print(f"⚠️ [Refinement Pool] Save failed: {e}")


def _infer_type_for_pool(place: dict) -> str:
    """장소 타입 간이 추론 (refinement pool용)"""
    name = place.get("name", "").lower()
    kw = place.get("keywords", {})
    menu_type = kw.get("menu_type", "") if isinstance(kw, dict) else ""

    if any(k in name or k in str(menu_type) for k in ["카페", "커피", "coffee", "디저트", "베이커리"]):
        return "카페"
    if any(k in name for k in ["호텔", "펜션", "게스트", "숙박"]):
        return "숙박"
    return "식당"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    input_text = request.message
    user_id = request.userId
    
    db = await get_database()
    session_doc = await db["user_trip_sessions"].find_one({"userId": user_id})
    
    survey_data = {}
    if session_doc:
        # reward.md 규격에 맞게 intent_context에서 데이터 추출
        intent_ctx = session_doc.get("intent_context", {})
        survey_data = intent_ctx.get("survey_data", {})
        
        # [NEW Logic] 채팅 히스토리 업데이트
        chat_msg = {"role": "user", "content": input_text, "timestamp": datetime.now().isoformat()}
        await db["user_trip_sessions"].update_one(
            {"userId": user_id},
            {
                "$push": {"intent_context.chat_history": chat_msg},
                "$set": {"last_activity_at": datetime.now().isoformat()}
            }
        )

    # [AGENT ROUTING]
    from langchain_core.messages import HumanMessage
    import json

    # Intent 분류
    intent = await classify_intent(input_text)

    # 개인화 컨텍스트 (course에서만 사용)
    personalization_ctx = ""
    if intent == "course":
        try:
            personalization_ctx = await build_personalization_context(db, user_id)
        except Exception as e:
            print(f"⚠️ [Context Builder] Failed: {e}")

    try:
        # 1. Intent에 따라 적절한 Agent 실행
        if intent == "general":
            from src.general_agent.graph import app as general_app
            print(f"🚀 [General Agent Start] User: {user_id}")
            result = await general_app.ainvoke({
                "messages": [HumanMessage(content=input_text)],
            })
        else:
            from src.agent.graph import app as agent_app
            print(f"🚀 [Course Agent Start] User: {user_id}")
            print(f"📊 [Survey Data] Region: {survey_data.get('region')}, Themes: {survey_data.get('themes')}")
            result = await agent_app.ainvoke({
                "messages": [HumanMessage(content=input_text)],
                "survey_data": survey_data,
                "userId": user_id,
                "personalization_context": personalization_ctx
            })
        
        # 2. 결과 추출
        final_answer_raw = result.get("final_answer", "")
        if isinstance(final_answer_raw, list):
            final_answer_raw = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in final_answer_raw])
        
        final_answer_raw = str(final_answer_raw) # 보장
        # 사진 매핑을 위한 enriched_results 추출
        enriched_results = result.get("enriched_results", [])
        
        # [FIX] 이름 기반 매핑으로 변경 (순서 의존성 제거)
        place_photo_map = {}
        
        def normalize_name(n):
            return n.replace(" ", "").lower() if n else ""

        if enriched_results:
            for item in enriched_results:
                p = item.get('place', {})
                p_name = p.get('name')
                p_photo = p.get('photo_name')
                
                if p_name and p_photo:
                    norm_key = normalize_name(p_name)
                    place_photo_map[norm_key] = p_photo
                    
        print(f"✅ [Agent Done] Output Length: {len(final_answer_raw)}, Photos: {len(place_photo_map)}")
        
        # 3. JSON 파싱 시도 (LLM Node에서 JSON으로 줄 예정)
        #    만약 텍스트만 오면 그대로 텍스트로 처리
        try:
            # 마크다운 코드 블록 제거 (```json ... ```)
            clean_json = final_answer_raw.strip()
            if clean_json.startswith("```"):
                import re
                # 첫 번째 ```json 또는 ``` 제거
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                # 마지막 ``` 제거
                clean_json = re.sub(r"\s*```$", "", clean_json)
            
            parsed_output = json.loads(clean_json)
            response_text = parsed_output.get("answer", str(final_answer_raw))
            
            # recommended_courses 파싱 (새로운 구조)
            recommended_courses = parsed_output.get("recommended_courses", [])
            
            # 기존 courses 필드도 fallback으로 지원
            if not recommended_courses:
                courses_data = parsed_output.get("courses", [])
                if courses_data:
                    recommended_courses = [{"course_id": 1, "course_name": "추천 코스", "places": courses_data}]
            
            all_courses = []  # 모든 코스의 EvidenceCard 리스트
            
            for course_idx, course in enumerate(recommended_courses):
                course_id = course.get("course_id", course_idx + 1)
                course_name = course.get("course_name", f"코스 {course_id}")
                places = course.get("places", [])
                
                course_cards = []
                for idx, place in enumerate(places):
                    # [FIX] 이름 기반 사진 매핑
                    place_name = place.get("name", "")
                    photo_name = None
                    
                    # 1. 이름으로 찾기
                    norm_name = normalize_name(place_name)
                    photo_name = place_photo_map.get(norm_name)
                    
                    # 2. Proxy URL 사용
                    api_url = os.getenv("API_URL", "http://localhost:8000")
                    img_url = f"{api_url}/api/photo?name={photo_name}" if photo_name else None
                    
                    course_cards.append(EvidenceCard(
                        placeId=place.get("id") or f"p{idx}",
                        name=place_name,
                        reason=place.get("reason", "추천 장소"),
                        reviewSummary=place.get("reason", "추천 장소"), 
                        risks="", 
                        trustScore=90,
                        keywords=[place.get("type", "장소")],
                        lat=place.get("lat"),
                        lng=place.get("lng"),
                        img=img_url
                    ))
                
                all_courses.append({
                    "course_id": course_id,
                    "course_name": course_name,
                    "course_description": course.get("course_description", ""),
                    "cards": course_cards
                })
            
            # 기본적으로 첫 번째 코스를 evidenceCards로 반환
            evidence_cards = all_courses[0]["cards"] if all_courses else []
            
            # 모든 코스 정보도 함께 전달 (프론트엔드에서 사용)
            # ChatResponse 모델에 allCourses 필드 추가 필요
                
        except json.JSONDecodeError:
            print("⚠️ JSON Parsing Failed, using raw text")
            response_text = final_answer_raw
            evidence_cards = []
            all_courses = []
        is_plan_request = bool(evidence_cards)
    except Exception as e:
        print(f"❌ [Agent Error] {e}")
        import traceback
        traceback.print_exc()
        
        # 에러 시 Fallback
        response_text = "죄송해요, 여행 정보를 찾는 중에 문제가 발생했어요. 잠시 후 다시 시도해 주세요."
        is_plan_request = False
        evidence_cards = []
        all_courses = []
    # (기존 Mock 로직 제거됨)
    
    # AI 응답을 history에 추가 및 상태 업데이트
    ai_msg = {"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()}
    update_fields = {
        "last_activity_at": datetime.now().isoformat()
    }
    if is_plan_request:
        update_fields["status"] = "COMPLETED" # 코스 생성 완료 시 상태 변경 (COMPLETED)
    
    await db["user_trip_sessions"].update_one(
        {"userId": user_id},
        {
            "$push": {"intent_context.chat_history": ai_msg},
            "$set": update_fields
        }
    )

    # [AUTO SAVE] 추천 코스 즉시 저장 (생성되면 바로 히스토리 저장)
    if is_plan_request and all_courses:
        try:
            group_id = str(uuid.uuid4())
            ts = datetime.now().isoformat()

            for course in all_courses:
                 # Cards -> Points 변환
                 points = []
                 cards_list = course.get("cards", [])
                 for card in cards_list:
                      # EvidenceCard 객체에서 속성 추출
                      points.append({
                          "id": str(card.placeId),
                          "name": card.name,
                          "lat": card.lat or 0.0,
                          "lng": card.lng or 0.0,
                          "desc": card.reason,
                          "img": card.img,
                          "tags": card.keywords,
                          "transport": "이동"
                      })

                 # DB Insert
                 new_session_id = str(uuid.uuid4())
                 new_session = {
                     "sessionId": new_session_id,
                     "group_id": group_id,
                     "userId": user_id,
                     "status": "COMPLETED_CANDIDATE",
                     "is_selected": False,
                     "title": course.get("course_name", "추천 코스"),
                     "course_description": course.get("course_description", "AI가 제안한 여행 코스입니다."),
                     "album_data": points,
                     "total_courses": len(points),
                     "ai_summary": response_text[:100] + "..." if response_text else "AI 추천",
                     "created_at": ts,
                     "completed_at": ts,
                     "last_activity_at": ts,
                     "intent_context": {"auto_saved": True}
                 }
                 await db["user_trip_sessions"].insert_one(new_session)

                 # 클라이언트가 이 ID를 알 수 있도록 course 객체 업데이트
                 course["course_id"] = new_session_id
                 course["group_id"] = group_id

            print(f"✅ Auto-saved {len(all_courses)} courses for user {user_id}")

        except Exception as e:
            print(f"⚠️ Auto-save failed: {e}")

    # all_courses를 CourseInfo 모델로 변환
    from backend.models.chat import CourseInfo
    all_courses_models = [CourseInfo(**c) for c in all_courses] if all_courses else None
    
    return ChatResponse(
        id=str(uuid.uuid4()),
        role="assistant",
        text=response_text,
        isDecisionPoint=is_plan_request,
        evidenceCards=evidence_cards,
        allCourses=all_courses_models,
        status="done"
    )


# ─────────────────────────────────────────────
# Input Validation Endpoint
# ─────────────────────────────────────────────

@router.post("/chat/validate", response_model=ValidateResponse)
async def validate_input(request: ValidateRequest):
    """
    사용자 입력이 여행/코스 추천에 유효한 질문인지 검증합니다.
    무의미한 입력(기호, 낙서, 관계없는 질문)을 걸러냅니다.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from pydantic import BaseModel, Field

    input_text = request.message.strip()

    # 빈 입력 즉시 거절
    if not input_text:
        return ValidateResponse(
            isValid=False,
            message="메시지를 입력해주세요!",
            suggestions=["설문조사 기반으로 코스 생성하기"]
        )

    # 너무 짧은 입력 (1~2글자이면서 의미 없는 경우) 빠르게 필터링
    if len(input_text) <= 2 and not any(kw in input_text for kw in ["맛집", "카페", "힐링", "산책", "데이트", "여행", "코스", "추천", "식당", "밥"]):
        return ValidateResponse(
            isValid=False,
            message="조금 더 구체적으로 알려주세요! 예를 들어 '동명동 맛집 추천' 같은 요청이면 더 좋은 코스를 만들 수 있어요.",
            suggestions=["설문조사 기반으로 코스 생성하기"]
        )

    # LLM 기반 검증
    class InputValidation(BaseModel):
        is_valid: bool = Field(description="입력이 여행/코스/맛집 관련 유효한 요청인지 여부")
        rejection_message: str = Field(
            default="",
            description="유효하지 않은 경우 사용자에게 보여줄 친절한 안내 메시지 (한국어)"
        )

    try:
        google_api_key = os.getenv("GOOGLE_API_KEY", "")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        llm = ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=google_api_key,
            temperature=0,
        )
        structured_llm = llm.with_structured_output(InputValidation)

        prompt = f"""당신은 광주광역시 여행/맛집 코스 추천 AI 챗봇의 입력 검증기입니다.
사용자의 입력이 여행 코스 추천에 유효한 요청인지 판단하세요.

**유효한 입력 (is_valid=true):**
- 장소/맛집/카페/관광지 추천 요청 (예: "동명동 카페 추천", "광주 맛집")
- 여행 테마/분위기 요청 (예: "힐링 코스", "데이트 코스", "가족 여행")
- 코스 생성 요청 (예: "바로 코스 짜줘", "오늘 뭐 먹지")
- 광주/여행 관련 질문 (예: "광주에 뭐가 유명해?")
- 음식/요리 관련 요청 (예: "한식 먹고 싶어", "디저트 추천")

**유효하지 않은 입력 (is_valid=false):**
- 무의미한 기호/글자 (예: "???", "ㅋㅋㅋ", "ㅎㅎㅎ", "asdf", "ㅁㄴㅇㄹ")
- 의미를 알 수 없는 낙서/장난 (예: "어쩔방구", "ㅇㅇ", "aaa", "ㅡㅡ")
- 여행/음식과 전혀 관계없는 요청 (예: "코딩해줘", "수학 풀어줘", "숙제 도와줘")
- 욕설이나 부적절한 표현

유효하지 않은 경우, rejection_message에 다음 중 적절한 메시지를 작성하세요:
- 무의미한 입력: "여행 관련 정보를 입력해주세요! 예를 들어 '동명동 데이트 코스' 같은 요청이면 맞춤 코스를 만들어 드릴게요 😊"
- 관계없는 요청: "저는 광주 여행 코스 추천 전문이에요! 가고 싶은 곳이나 원하는 분위기를 알려주시면 딱 맞는 코스를 추천해 드릴게요."

사용자 입력: "{input_text}"
"""

        result = await structured_llm.ainvoke(prompt)

        if result.is_valid:
            return ValidateResponse(isValid=True, message="")
        else:
            return ValidateResponse(
                isValid=False,
                message=result.rejection_message or "여행 관련 정보를 입력해주세요! 예를 들어 '동명동 데이트 코스' 같은 요청이면 맞춤 코스를 만들어 드릴게요.",
                suggestions=["설문조사 기반으로 코스 생성하기"]
            )

    except Exception as e:
        print(f"⚠️ [Validate] Error: {e}")
        # 검증 실패 시 일단 유효한 것으로 처리 (파이프라인에서 처리)
        return ValidateResponse(isValid=True, message="")
