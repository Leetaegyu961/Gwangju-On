"""
Aggregator Node
병렬로 생성된 코스 결과들을 하나로 취합하여 최종 응답을 포맷팅합니다.
"""

import json
from typing import Any
from ..state import AgentState

async def aggregator_node(state: AgentState) -> dict[str, Any]:
    """
    generated_courses 리스트를 취합하여 최종 JSON 응답을 생성합니다.
    """
    generated_courses = state.get("generated_courses", [])
    
    if not generated_courses:
        return {
            "final_answer": json.dumps({
                "answer": "죄송합니다. 코스를 생성하는 데 실패했습니다.",
                "recommended_courses": []
            }, ensure_ascii=False)
        }
    
    # course_id 기준으로 정렬 (1, 2, 3 순서 보장)
    # 가끔 LLM이 id를 누락할 수 있으므로 get(..., 99)로 뒤로 보냄
    generated_courses.sort(key=lambda x: x.get("course_id", 99))
    
    # 최종 응답 구조 생성
    final_response = {
        "answer": f"{len(generated_courses)}가지 테마의 맞춤형 코스를 추천해 드립니다.",
        "recommended_courses": generated_courses
    }
    
    # JSON 문자열로 변환
    final_json = json.dumps(final_response, ensure_ascii=False, indent=2)
    
    print(f"[OK] [Aggregator] 최종 응답 생성 완료 ({len(generated_courses)}개 코스)")
    
    return {
        "final_answer": final_json,
        "current_step": "responding"
    }
