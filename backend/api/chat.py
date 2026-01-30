from fastapi import APIRouter
from backend.models.chat import ChatRequest, ChatResponse, EvidenceCard
import time
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    input_text = request.message
    user_id = request.userId # Request에 userId가 있다고 가정 (Typescript Interface 업데이트 필요할 수 있음)
    
    # [Context Retrieval] MongoDB 또는 In-Memory DB에서 Survey Data 조회
    from backend.api.user import USER_DB
    from backend.db import get_database
    
    survey_data = USER_DB.get(user_id, {})
    if not survey_data:
        db = await get_database()
        session_doc = await db["user_trip_sessions"].find_one({"userId": user_id})
        if session_doc:
            session_doc.pop("_id", None)
            # 평탄화하여 에이전트가 처리하기 쉽게 변환 (필요시)
            survey_data = {
                **session_doc.get("demographics", {}),
                **session_doc.get("survey_data", {}),
                "created_at": session_doc.get("created_at")
            }
            # 메모리 캐싱
            USER_DB[user_id] = survey_data
    
    # [REAL AGENT INTEGRATION]
    from langchain_core.messages import HumanMessage
    from src.agent.graph import app as agent_app  # agent_app import 필요 (파일 상단으로 이동 권장)
    import json

    try:
        # 1. Agent 실행
        print(f"🚀 [Agent Start] User: {user_id}")
        print(f"📊 [Survey Data] Region: {survey_data.get('region')}, Themes: {survey_data.get('themes')}")
        result = await agent_app.ainvoke({
            "messages": [HumanMessage(content=input_text)],
            "survey_data": survey_data
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
                    img_url = f"http://localhost:8000/api/photo?name={photo_name}" if photo_name else None
                    
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
    
    # 4. 코스 생성 완료 시 DB 상태 업데이트 (status: completed)
    if is_plan_request:
        db = await get_database()
        await db["user_trip_sessions"].update_one(
            {"userId": user_id},
            {"$set": {"status": "completed"}}
        )
        print(f"🎯 [Status Update] Session for {user_id} set to completed")

    # all_courses를 CourseInfo 모델로 변환
    from backend.models.chat import CourseInfo
    all_courses_models = [CourseInfo(**c) for c in all_courses] if all_courses else None
    
    return ChatResponse(
        id=str(uuid.uuid4()),
        role="assistant",
        text=response_text,
        isDecisionPoint=is_plan_request, # 코스가 있으면 결정 포인트로 간주
        evidenceCards=evidence_cards,
        allCourses=all_courses_models,
        status="done"
    )
