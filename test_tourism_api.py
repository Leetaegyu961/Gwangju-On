import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
MY_API_KEY = os.getenv("REFERENCE_API_")

def get_data_force():
    if not MY_API_KEY: return

    # ★ 검색(searchKeyword) 대신 목록 조회(areaBasedList) 사용
    url = 'http://apis.data.go.kr/B551011/TarRlteTarService1/areaBasedList1'
    
    # 2025년 1월, 광주(5), 북구(4)의 모든 관광지 다 가져오기
    params = {
        'serviceKey': MY_API_KEY,
        'numOfRows': '100',      # 넉넉하게 100개 요청
        'pageNo': '1',
        'MobileOS': 'ETC',
        'MobileApp': 'TestApp',
        'baseYm': '202501',
        'areaCd': '29',           # 광주
        'signguCd': '29170',         # 북구 (무등산이 여기 있을 확률 높음)
        '_type': 'json'
    }

    print(f"📡 광주 북구 전체 데이터 조회 중... (무등산 찾기)")

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        items = data['response']['body']['items']
        if items == "":
            print("❌ 데이터 없음. (지역 코드 문제거나 해당 월 데이터 누락)")
            return

        item_list = items.get('item', [])
        
        # 전체 데이터 JSON 파일로 저장
        save_path = "data/tourism_data_full.json"
        
        # data 폴더가 없으면 생성 (혹시 모르니)
        if not os.path.exists("data"):
            os.makedirs("data")

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(item_list, f, ensure_ascii=False, indent=2)

        print(f"✅ 전체 데이터 {len(item_list)}건 저장 완료!")
        print(f"📂 저장 위치: {os.path.abspath(save_path)}")

    except Exception as e:
        print(f"에러: {e}")

if __name__ == "__main__":
    get_data_force()