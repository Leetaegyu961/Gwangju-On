"""
Refine Agent Package
코스 생성 후 부분 수정을 담당하는 경량 에이전트.

기존 에이전트와의 차이:
- agent (src/agent/): 전체 코스 생성 파이프라인 (28초, LangGraph 8개 노드)
- mini_agent (src/mini_agent/): 개별 장소 정보 조회 (간결 요약)
- refine_agent (src/refine_agent/): 코스 부분 수정 (2~3초, Gemini 1회 + 규칙 기반)
"""

from .intent_analyzer import analyze_refinement_intent, RefinementIntent
from .course_modifier import apply_modification

__all__ = ["analyze_refinement_intent", "RefinementIntent", "apply_modification"]
