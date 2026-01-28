"""
Summarization Node
Naver Blog Search 결과를 병렬로 정제/요약하여 핵심 정보만 추출합니다.
"""

import asyncio
from typing import Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from ..config import config
from ..state import AgentState


async def _summarize_single_blog(llm: ChatGoogleGenerativeAI, blog: dict, place_name: str) -> dict:
    """단일 블로그 글을 LLM을 통해 정제/요약합니다."""
    content = blog.get('full_content', '')
    if not content:
        return blog
    
    # 너무 짧으면 요약 스킵
    if len(content) < 100:
        return blog

    # 프롬프트: 핵심 정보 추출 및 정제
    prompt = f"""다음 문서는 '{place_name}'에 대한 블로그 리뷰입니다.
여행자에게 실제로 도움이 되는 정보 위주로 **핵심 내용만 정제**해주세요.

[지침]
1. 단순 인사말, 광고성 멘트, 감탄사, 이모티콘 남발은 제거하세요.
2. 아래 항목 위주로 정보를 정리하세요:
   - 맛/메뉴 평가 (구체적인 메뉴명 포함)
   - 분위기/인테리어 (사진 찍기 좋은지 등)
   - 서비스/친절도
   - 꿀팁 (웨이팅, 주차, 예약 등)
3. 문장 형태보다는 **간결한 개조식(Bullet points)**으로 요약하세요.
4. 분량은 원문의 30% 정도로 줄이되, 중요 정보는 누락하지 마세요.

[블로그 원문]
{content[:10000]} (너무 길면 자름)

[정제된 내용]:"""

    try:
        # 비동기 LLM 호출
        response = await llm.ainvoke(prompt)
        
        # 원본 구조 유지하되 content를 교체
        new_blog = blog.copy()
        new_blog['full_content'] = response.content
        new_blog['is_summarized'] = True
        return new_blog
        
    except Exception as e:
        print(f"  ⚠️ 블로그 요약 실패 ({place_name}): {e}")
        return blog


async def summarization_node(state: AgentState) -> dict[str, Any]:
    """
    수집된 블로그 데이터를 병렬로 요약/정제하는 노드입니다.
    """
    enriched_results = state.get("enriched_results")
    if not enriched_results:
        return {"summarized_results": None}
    
    print(f"\n🧪 데이터 정제/요약 시작 (Input: {len(enriched_results)}개 장소)")
    
    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0.3, 
    )
    
    # 모든 장소의 모든 블로그에 대해 태스크 생성
    all_tasks = []
    
    # 구조 복원을 위해 (장소 인덱스, 블로그 리스트) 매핑
    # 하지만 gather는 순서를 보장하므로, 리스트 컴프리헨션으로 처리하는 게 깔끔하지 않음 (이중 루프라)
    # 따라서 장소별로 비동기 처리를 묶는 함수를 만듭니다.
    
    async def process_place(place_item):
        """한 장소에 속한 블로그들을 병렬 처리"""
        place_name = place_item['place']['name']
        blogs = place_item.get('blogs', [])
        
        if not blogs:
            return place_item
        
        # 블로그별 병렬 요약 요청
        blog_tasks = [
            _summarize_single_blog(llm, blog, place_name)
            for blog in blogs
        ]
        
        # 한 장소 내의 블로그들이 다 끝날 때까지 대기
        summarized_blogs = await asyncio.gather(*blog_tasks)
        
        new_item = place_item.copy()
        new_item['blogs'] = summarized_blogs
        return new_item

    # 장소 단위로 병렬 실행
    place_tasks = [process_place(item) for item in enriched_results]
    
    summarized_results = await asyncio.gather(*place_tasks)
    
    print(f"✅ 데이터 정제 완료")
    
    return {"summarized_results": summarized_results}
