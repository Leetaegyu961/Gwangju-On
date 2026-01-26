"""
Public Data Node (광주 맛집 JSON 데이터)
로컬 JSON 파일에 있는 '광주 맛집 리스트'를 로드하고, 스코어링 시스템에 활용할 수 있도록 데이터를 제공하는 노드입니다.

# 한국관광공사_관광지별 연관 관광지 정보 (추후 확장을 위해 명시)
"""

import os
import json
from typing import Any
from ..state import AgentState

# JSON 파일 경로 (프로젝트 루트 기준)
# 예: data/gwangju_food_list.json
DATA_FILE_PATH = "data/gwangju_food_list.json"


def _load_food_list_from_json(file_path: str) -> list[dict]:
    """
    JSON 파일에서 맛집 리스트를 로드합니다.
    Pandas 의존성 없이 Python 내장 라이브러리만 사용하므로 가볍고 빠릅니다.
    """
    if not os.path.exists(file_path):
        print(f"⚠️ [Public Data] JSON 파일을 찾을 수 없습니다: {file_path}")
        return []
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # JSON 구조: 보통 리스트 형태 ([{}, {}, ...])이거나, 특정 키 안에 리스트가 있는 형태 ({ "results": [...] })
        if isinstance(data, list):
            food_list = data
        elif isinstance(data, dict) and "data" in data: # 공공데이터 포털 형식 등
            food_list = data["data"]
        else:
            food_list = [data] # 단일 객체일 경우

        print(f"📊 [Public Data] 맛집 데이터 로드 완료: {len(food_list)}개")
        return food_list
        
    except json.JSONDecodeError as e:
        print(f"⚠️ [Public Data] JSON 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"⚠️ [Public Data] 로드 중 알 수 없는 오류: {e}")
        return []


def public_data_search_node(state: AgentState) -> dict[str, Any]:
    """
    JSON 기반의 공공데이터(맛집 리스트)를 조회하여 후보군을 제공하는 노드입니다.
    
    이 데이터는 추후 스코어링 시스템의 평가 항목 중 하나(예: '공공데이터 인증 맛집 가산점')로 사용될 예정입니다.
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        업데이트된 상태 ({'public_data_results': ...})
    """
    
    # 1. 파일 경로 설정
    base_dir = os.getcwd()
    json_path = os.path.join(base_dir, "data", "gwangju_food_list.json")
    
    # 2. 데이터 로드 (매번 로드하지 않고 캐싱하는 방법도 고려 가능하나, 50개 수준이면 매번 읽어도 무방)
    #    (성능 최적화가 필요하면 전역 변수에 로드해두고 재사용 가능)
    food_list = _load_food_list_from_json(json_path)
    
    if not food_list:
        print("ℹ️ [Public Data] 로드된 데이터가 없습니다.")
        return {"public_data_results": None}

    print(f"🏛️ [Public Data] 광주 맛집 리스트 조회 (총 {len(food_list)}건)")

    # 3. 데이터 반환 
    # (여기서 필터링을 할 수도 있지만, 우선은 전체 데이터를 넘겨서 LLM이나 Scoring 로직이 판단하게 함)
    return {"public_data_results": food_list}
