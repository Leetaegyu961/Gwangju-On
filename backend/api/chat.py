from fastapi import APIRouter
from backend.models.chat import ChatRequest, ChatResponse, EvidenceCard, RecommendedCourse
import time
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    input_text = request.message
    user_id = request.userId # Request에 userId가 있다고 가정 (Typescript Interface 업데이트 필요할 수 있음)
    
    # [In-Memory DB] Survey Data 조회
    from backend.api.user import USER_DB
    survey_data = USER_DB.get(user_id, {})
    
    # [REAL AGENT INTEGRATION]
    from langchain_core.messages import HumanMessage
    from src.agent.graph import app as agent_app  # agent_app import 필요 (파일 상단으로 이동 권장)
    import json

    try:
        # 1. Agent 실행
        print(f"🚀 [Agent Start] User: {user_id}")
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
        place_photos = {}
        if enriched_results:
            # Enriched Results 순환 시 index를 사용하여 p1, p2, p3... 키 생성
            for idx, item in enumerate(enriched_results, 1):
                temp_id = f"p{idx}"
                p = item.get('place', {})
                if p.get('photo_name'):
                    place_photos[temp_id] = p['photo_name']
                    
        print(f"✅ [Agent Done] Output Length: {len(final_answer_raw)}, Photos: {len(place_photos)}")
        
        # 3. JSON 파싱 시도 (LLM Node에서 JSON으로 줄 예정)
        #    만약 텍스트만 오면 그대로 텍스트로 처리
        final_courses = []
        evidence_cards = []
        
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
            
            # [Multi-Course Parsing Logic]
            raw_courses = parsed_output.get("recommended_courses", [])
            
            if raw_courses:
                for course in raw_courses:
                    course_places = []
                    for idx, place in enumerate(course.get("places", [])):
                        # ID Mapping & Photo URL Logic
                        place_id = place.get("id") or f"p{idx}"
                        photo_name = place_photos.get(place_id)
                        img_url = f"http://localhost:8000/api/photo?name={photo_name}" if photo_name else None
                        
                        course_places.append(EvidenceCard(
                            placeId=place_id,
                            name=place.get("name"),
                            reason=place.get("reason", "추천 장소"),
                            reviewSummary=place.get("reason", "추천 장소"), 
                            risks="", 
                            trustScore=90,
                            keywords=[place.get("type", "장소")],
                            lat=place.get("lat"),
                            lng=place.get("lng"),
                            img=img_url 
                        ))
                    
                    final_courses.append(RecommendedCourse(
                        course_id=course.get("course_id", 0),
                        course_name=course.get("course_name", "추천 코스"),
                        course_description=course.get("course_description", ""),
                        places=course_places,
                        total_budget=course.get("total_budget", "")
                    ))
                
                # Fallback: 첫 번째 코스를 evidenceCards로 설정 (하위 호환성)
                if final_courses:
                    evidence_cards = final_courses[0].places
            
            # 구버전 호환 (courses 키가 없고 기존 필드만 있는 경우 - 거의 없을 듯)
            elif parsed_output.get("courses"):
                # ...legacy logic if needed...
                pass
                
        except json.JSONDecodeError:
            print("⚠️ JSON Parsing Failed, using raw text")
            response_text = final_answer_raw
            final_courses = []
            evidence_cards = []
            
        is_plan_request = bool(final_courses)
        
    except Exception as e:
        print(f"❌ [Agent Error] {e}")
        import traceback
        traceback.print_exc()
        
        # 에러 시 Fallback
        response_text = "죄송해요, 여행 정보를 찾는 중에 문제가 발생했어요. 잠시 후 다시 시도해 주세요."
        is_plan_request = False
        final_courses = []
        evidence_cards = []
    
    return ChatResponse(
        id=str(uuid.uuid4()),
        role="assistant",
        text=response_text,
        isDecisionPoint=is_plan_request, # 코스가 있으면 결정 포인트로 간주
        evidenceCards=evidence_cards,
        courses=final_courses, # [New Field]
        status="done"
    )
