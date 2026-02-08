"""
Mini Agent Nodes - LLM Node
LangSmith 추적을 위한 독립적인 LLM 노드
"""

from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import config


class LLMNode:
    """
    LLM 응답 생성 노드
    LangSmith에서 독립적으로 추적됩니다.
    """
    
    def __init__(self, model: str = None):
        self.model_name = model or config.GEMINI_MODEL
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.7,
        )
    
    async def generate_summary(
        self, 
        query: str, 
        places: List[Dict[str, Any]]
    ) -> str:
        """
        장소 정보를 기반으로 간결한 요약 생성
        
        Args:
            query: 사용자 검색 쿼리
            places: 장소 정보 리스트
            
        Returns:
            LLM이 생성한 요약 텍스트
        """
        print(f"🧠 [LLMNode] 요약 생성 시작")
        
        # 컨텍스트 구성
        context = self._build_context(places)
        
        # 프롬프트 생성
        prompt = self._build_prompt(query, context)
        
        try:
            # LangSmith 추적을 위한 메타데이터 설정
            response = await self.llm.ainvoke(
                prompt,
                config={"run_name": "MiniAgent_LLM_Summary"}
            )
            print(f"✅ [LLMNode] 요약 생성 완료")
            return response.content
        except Exception as e:
            print(f"⚠️ [LLMNode] 오류: {e}")
            return "정보를 요약하는 데 문제가 발생했습니다."
    
    def _build_context(self, places: List[Dict[str, Any]]) -> str:
        """장소 정보를 컨텍스트 문자열로 변환"""
        context_parts = []
        
        for idx, place in enumerate(places, 1):
            place_info = f"""## {idx}. {place.get('name', '알 수 없음')}
- 주소: {place.get('address', '')}
- 평점: ⭐{place.get('rating', 0)} ({place.get('total_reviews', 0)}개 리뷰)
"""
            
            # RAG 키워드 정보 추가 (VectorDB에서 가져온 경우)
            keywords = place.get("keywords", {})
            if keywords:
                if keywords.get("menu_type"):
                    place_info += f"- 종류: {keywords['menu_type']}\n"
                if keywords.get("signature_menu"):
                    menus = keywords['signature_menu']
                    if isinstance(menus, list):
                        menus = ", ".join(menus[:3])
                    place_info += f"- 대표메뉴: {menus}\n"
                if keywords.get("ambiance"):
                    ambiance = keywords['ambiance']
                    if isinstance(ambiance, list):
                        ambiance = ", ".join(ambiance[:3])
                    place_info += f"- 분위기: {ambiance}\n"
            else:
                # 기존 방식 (Google Places API에서 가져온 경우)
                reviews = place.get("reviews", [])
                if reviews:
                    place_info += "### 리뷰 요약:\n"
                    for r in reviews[:2]:
                        text = r.get('text', '')[:80]
                        place_info += f"- \"{text}...\"\n"
            
            context_parts.append(place_info)
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """LLM 프롬프트 생성"""
        return f"""당신은 간결하고 친절한 장소 추천 전문가입니다.

사용자 질문: "{query}"

검색된 장소 정보:
{context}

위 정보를 바탕으로 해당 장소를 **불릿 포인트 3개 이하**로 간결하게 요약하세요.

형식:
• 핵심 특징 1
• 핵심 특징 2  
• 핵심 특징 3 (선택)

규칙:
- 각 불릿은 15자 이내로 작성
- 이모지 1개씩 포함
- 친근한 말투 사용
- 불필요한 서론/마무리 없이 바로 불릿만 출력
"""
