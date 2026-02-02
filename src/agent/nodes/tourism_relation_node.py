"""
Tourism Relation Node (한국관광공사 연관 관광지)
특정 관광지를 검색했을 때, 한국관광공사 빅데이터 API를 통해 연관된 관광지 정보를 제공하는 노드입니다.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import Any
from dotenv import load_dotenv

from ..state import AgentState

load_dotenv()

# .env에서 디코딩 키를 가져옴 (REFERENCE_API_)
# 주의: 공공데이터포털 API는 Decoding Key를 사용하는 것이 일반적.
# requests 라이브러리가 자동으로 URL 인코딩을 수행하기 때문입니다.
TOURISM_API_KEY = os.getenv("REFERENCE_API_", "")

def _get_related_tourist_spots(keyword: str, max_rows: int = 5) -> list[dict]:
    """
    한국관광공사 타겟마케팅 등 API (연관 관광지 조회)
    Endpoint: http://apis.data.go.kr/B551011/TarRlteTarService1/searchKeyword1
    """
    if not TOURISM_API_KEY:
        print("⚠️ [Tourism] API Key가 없습니다. (REFERENCE_API_)")
        return []

    url = 'http://apis.data.go.kr/B551011/TarRlteTarService1/searchKeyword1'
    
    # 조회 기준 연월: 4달 전 (데이터가 확실히 있는 시점, API 업데이트 주기에 따라 최신 달은 없을 수 있음)
    # 예: 오늘이 2024년 5월이면 -> 202401
    target_date = datetime.now() - timedelta(days=120)
    base_ym = target_date.strftime("%Y%m")

    params = {
        'serviceKey': TOURISM_API_KEY,  # Decoding Key 권장
        'numOfRows': str(max_rows),
        'pageNo': '1',
        'MobileOS': 'ETC',
        'MobileApp': 'GwangjuOn',
        'baseYm': base_ym,              # 최근 데이터
        'areaCd': '',                   # 전국 대상 (광주 필터링은 후처리로 할 수도 있음)
        'signguCd': '',
        'keyword': keyword,
        '_type': 'json'                 # JSON 응답 필수
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status() # 4xx, 5xx 에러 체크
        
        data = response.json()
        
        # 응답 구조 파싱
        # response > body > items > item
        body = data.get('response', {}).get('body', {})
        items = body.get('items', {})
        
        if not items:
            print(f"ℹ️ [Tourism] '{keyword}'에 대한 연관 관광지 데이터 없음")
            return []
            
        item_list = items.get('item', [])
        
        # 리스트가 아니라 단일 딕셔너리로 올 경우 처리
        if isinstance(item_list, dict):
            item_list = [item_list]
            
        # 필요한 필드만 추출
        results = []
        for item in item_list:
            results.append({
                "name": item.get('rlteTatsNm', '알수없음'),    # 연관 관광지 이름
                "category": item.get('rlteCtgryMclsNm', ''),  # 중분류 (음식, 쇼핑 등)
                "rank": item.get('rlteRank', '0'),            # 순위
                "target_name": item.get('tAtsNm', '')         # 원본 검색어
            })
            
        print(f"📊 [Tourism] '{keyword}' 연관 관광지 {len(results)}개 발견")
        return results

    except Exception as e:
        print(f"⚠️ [Tourism] API 호출 중 오류: {e}")
        # 디버깅용: 응답 내용을 찍어볼 수 있음
        # print(response.text)
        return []


async def tourism_relation_node(state: AgentState) -> dict[str, Any]:
    """
    사용자 쿼리나 현재 검색된 장소들을 기반으로 '연관 관광지'를 추천받는 노드입니다.
    
    Args:
        state: AgentState
        
    Returns:
        {"tourism_data": [...]}
    """
    
    # 1. 검색 키워드 결정
    # 시나리오 A: 사용자가 입력한 검색어에서 키워드 추출 (QueryPlan 활용)
    # 시나리오 B: 앞단(Google Place)에서 찾은 주요 장소 이름을 사용
    
    query_plan = state.get("query_plan")
    keywords = []
    
    if query_plan and query_plan.get("place_queries"):
        # 검색어 리스트에서 '광주', '동명동' 등 지역명 제외하고 핵심만 뽑기는 어렵지만,
        # 일단 쿼리 자체를 넣어보거나, 특정 장소명을 넣는 게 좋음.
        # 예: "광주 동명동 카페" -> "동명동" (이런 전처리가 필요할 수 있음)
        # 우선은 place_queries의 첫 번째 값을 사용하되, 너무 길면 비효율적일 수 있음.
        
        # 여기서는 테스트를 위해 하드코딩된 인기 관광지나, 
        # 혹은 기 검색된 Place 결과의 첫 번째 가게 이름을 넣어볼 수 있음.
        pass

    # [테스트용] 만약 찾은 Place가 있다면 그 중 1등 가게의 이름으로 연관 장소를 찾아본다.
    place_data = state.get("place_data", [])
    if place_data:
        # 첫 번째 장소의 이름 사용 (예: "오디너리 디저트")
        target_place = place_data[0]['name']
        print(f"🔗 [Tourism] '{target_place}'의 연관 관광지를 검색합니다.")
        keywords.append(target_place)
    else:
        # Place 데이터가 아직 없다면 쿼리 플랜에서 유추 (단순화: '동명동' 같은 지역명 사용이 유리)
        # 임시로 '동명동' 카페거리 키워드 사용 (예시)
        # 실전에서는 LLM이 추출한 'region' 정보를 쓰는 게 좋음
        keywords.append("동명동")

    all_results = []
    
    for kw in keywords:
        results = _get_related_tourist_spots(kw)
        all_results.extend(results)
        
    return {"tourism_data": all_results}
