"""
음식점 스코어링 시스템
다양한 데이터 소스를 통합하여 음식점에 점수를 부여하고 Top N 추천 리스트를 생성합니다.
"""

import os
import json
import re
import math
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher


class RestaurantScoringSystem:
    """
    음식점 스코어링 및 랭킹 시스템
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Args:
            data_dir: 공공 데이터 JSON 파일들이 위치한 디렉토리 경로
        """
        self.data_dir = data_dir
        self.exemplary_restaurants = []  # 모범 음식점 리스트
        self.gwangju_food_list = []      # 광주 맛집 리스트
        
    def load_public_datasets(self) -> None:
        """
        공공 데이터(모범 음식점, 광주 맛집)를 로드합니다.
        """
        # 1. 모범 음식점 로드
        exemplary_path = os.path.join(self.data_dir, "Gwangju City Certified Exemplary Restaurant.json")
        if os.path.exists(exemplary_path):
            try:
                with open(exemplary_path, 'r', encoding='utf-8') as f:
                    self.exemplary_restaurants = json.load(f)
                print(f"✅ 모범 음식점 데이터 로드: {len(self.exemplary_restaurants)}개")
            except Exception as e:
                print(f"⚠️ 모범 음식점 로드 실패: {e}")
        else:
            print(f"⚠️ 모범 음식점 파일 없음: {exemplary_path}")
        
        # 2. 광주 맛집 리스트 로드
        food_list_path = os.path.join(self.data_dir, "gwangju_food_list.json")
        if os.path.exists(food_list_path):
            try:
                with open(food_list_path, 'r', encoding='utf-8') as f:
                    self.gwangju_food_list = json.load(f)
                print(f"✅ 광주 맛집 리스트 로드: {len(self.gwangju_food_list)}개")
            except Exception as e:
                print(f"⚠️ 광주 맛집 로드 실패: {e}")
        else:
            print(f"⚠️ 광주 맛집 파일 없음: {food_list_path}")
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        음식점 이름을 정규화합니다 (공백, 특수문자 제거).
        
        Args:
            name: 원본 음식점 이름
            
        Returns:
            정규화된 이름
        """
        if not name:
            return ""
        # 공백 제거
        normalized = name.replace(" ", "").replace("\t", "")
        # 괄호 안 내용 제거 (예: "고려조삼계탕 (상무점)" -> "고려조삼계탕")
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        # 특수문자 제거 (한글, 숫자, 영문만 남김)
        normalized = re.sub(r'[^\w가-힣]', '', normalized)
        return normalized.lower()
    
    @staticmethod
    def extract_district(address: str) -> str:
        """
        주소에서 구/동 정보를 추출합니다.
        
        Args:
            address: 전체 주소
            
        Returns:
            구/동 정보 (예: "서구 치평동")
        """
        if not address:
            return ""
        
        # "광주광역시" 제거
        address = address.replace("광주광역시", "").strip()
        
        # 구 추출
        district = ""
        for part in address.split():
            if part.endswith("구"):
                district = part
                break
        
        # 동/읍/면 추출
        dong = ""
        for part in address.split():
            if any(part.endswith(suffix) for suffix in ["동", "읍", "면"]):
                # 괄호 안에 있는 동 이름 제거 (예: "(치평동)" -> "치평동")
                dong = re.sub(r'[()]', '', part)
                break
        
        return f"{district} {dong}".strip()
    
    def match_restaurant(self, name: str, address: str) -> Dict[str, bool]:
        """
        주어진 음식점이 공공 데이터에 포함되는지 확인합니다.
        
        Args:
            name: 음식점 이름
            address: 음식점 주소
            
        Returns:
            {"is_exemplary": bool, "is_gwangju_food": bool}
        """
        normalized_name = self.normalize_name(name)
        district = self.extract_district(address)
        
        result = {
            "is_exemplary": False,
            "is_gwangju_food": False
        }
        
        # 1. 모범 음식점 매칭
        for restaurant in self.exemplary_restaurants:
            ref_name = self.normalize_name(restaurant.get("명칭", ""))
            ref_address = restaurant.get("주소", "")
            ref_district = self.extract_district(ref_address)
            
            # 이름 일치 확인 (정확 매칭 또는 유사도 90% 이상)
            if normalized_name == ref_name:
                result["is_exemplary"] = True
                break
            elif normalized_name and ref_name:
                similarity = SequenceMatcher(None, normalized_name, ref_name).ratio()
                if similarity >= 0.9 and district == ref_district:
                    result["is_exemplary"] = True
                    break
        
        # 2. 광주 맛집 매칭
        for restaurant in self.gwangju_food_list:
            ref_name = self.normalize_name(restaurant.get("name", ""))
            ref_address = restaurant.get("address", "")
            ref_district = self.extract_district(ref_address)
            
            # 이름 일치 확인
            if normalized_name == ref_name:
                result["is_gwangju_food"] = True
                break
            elif normalized_name and ref_name:
                similarity = SequenceMatcher(None, normalized_name, ref_name).ratio()
                if similarity >= 0.9 and district == ref_district:
                    result["is_gwangju_food"] = True
                    break
        
        return result
    
    def calculate_score(self, enriched_item: Dict) -> Tuple[float, Dict]:
        """
        개별 음식점의 총점을 계산합니다.
        
        Args:
            enriched_item: {
                "place": {...},  # Google Places 데이터
                "blogs": [...]   # Naver 블로그 데이터
            }
            
        Returns:
            (총점, 점수 세부내역)
        """
        place = enriched_item.get("place", {})
        blogs = enriched_item.get("blogs", [])
        
        name = place.get("name", "")
        address = place.get("address", "")
        rating = place.get("rating", 0.0)
        user_ratings_total = place.get("user_ratings_total", 0)
        
        # 점수 세부내역
        breakdown = {
            "exemplary": 0,
            "gwangju_food": 0,
            "blogs": 0,
            "rating": 0,
            "reviews": 0
        }
        
        # 1. 공공 데이터 점수 (가중치 조정: 3점 -> 1점)
        # 인증 맛집으로만 추천이 몰리는 것을 방지하기 위해 가중치 낮춤
        match_result = self.match_restaurant(name, address)
        if match_result["is_exemplary"]:
            breakdown["exemplary"] = 1
        if match_result["is_gwangju_food"]:
            breakdown["gwangju_food"] = 1
        
        # 2. 블로그 점수 (개수 기반 점수 제거)
        # 사용자 피드백 반영: 블로그 개수는 편향이 심하므로 점수에서 제외
        # 감성 분석은 scoring_node에서 LLM으로 수행
        breakdown["blogs"] = 0
        
        # 3. Google Places 평점 점수 (최대 2점)
        if rating > 0:
            breakdown["rating"] = round((rating / 5.0) * 2, 2)
        
        # 4. Google Places 리뷰 수 점수 (최대 2점)
        if user_ratings_total > 0:
            # log10 스케일 사용 (리뷰가 많을수록 증가하지만 체감 감소)
            breakdown["reviews"] = round(min(2.0, math.log10(user_ratings_total + 1) * 0.5), 2)
        
        # 총점 계산
        total_score = sum(breakdown.values())
        
        return round(total_score, 2), breakdown
    
    def rank_restaurants(self, enriched_results: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        음식점 리스트를 점수 기준으로 정렬하여 Top N을 반환합니다.
        
        Args:
            enriched_results: [{"place": {...}, "blogs": [...}}, ...]
            top_n: 상위 몇 개를 반환할지
            
        Returns:
            점수가 포함된 음식점 리스트 (내림차순 정렬)
        """
        if not enriched_results:
            return []
        
        scored_results = []
        
        for item in enriched_results:
            total_score, breakdown = self.calculate_score(item)
            
            scored_item = {
                **item,  # 기존 place, blogs 정보 유지
                "score": total_score,
                "score_breakdown": breakdown
            }
            scored_results.append(scored_item)
        
        # 점수 기준 내림차순 정렬
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Top N 반환
        return scored_results[:top_n]
    
    def print_ranking(self, scored_results: List[Dict], top_n: int = 5) -> None:
        """
        스코어링 결과를 보기 좋게 출력합니다.
        
        Args:
            scored_results: rank_restaurants()의 반환값
            top_n: 출력할 상위 개수
        """
        print(f"\n{'='*60}")
        print(f"🏆 스코어링 결과 Top {top_n}")
        print(f"{'='*60}\n")
        
        for idx, item in enumerate(scored_results[:top_n], 1):
            place = item.get("place", {})
            score = item.get("score", 0)
            breakdown = item.get("score_breakdown", {})
            
            name = place.get("name", "Unknown")
            address = place.get("address", "")
            
            print(f"{idx}. {name} ({score}점)")
            print(f"   주소: {address}")
            print(f"   점수 세부:")
            print(f"     - 모범음식점: {'✅' if breakdown['exemplary'] > 0 else '❌'} (+{breakdown['exemplary']})")
            print(f"     - 광주맛집: {'✅' if breakdown['gwangju_food'] > 0 else '❌'} (+{breakdown['gwangju_food']})")
            print(f"     - 블로그: {len(item.get('blogs', []))}개 (+{breakdown['blogs']})")
            print(f"     - 평점: {place.get('rating', 0)}/5.0 (+{breakdown['rating']})")
            print(f"     - 리뷰: {place.get('user_ratings_total', 0)}개 (+{breakdown['reviews']})")
            print()
        
        print(f"{'='*60}\n")


# 싱글톤 인스턴스 생성
_scoring_system_instance = None

def get_scoring_system(data_dir: str = "data") -> RestaurantScoringSystem:
    """
    스코어링 시스템 싱글톤 인스턴스를 반환합니다.
    
    Args:
        data_dir: 데이터 디렉토리 경로
        
    Returns:
        RestaurantScoringSystem 인스턴스
    """
    global _scoring_system_instance
    
    if _scoring_system_instance is None:
        _scoring_system_instance = RestaurantScoringSystem(data_dir)
        _scoring_system_instance.load_public_datasets()
    
    return _scoring_system_instance

class PersonalizedScoringSystem(RestaurantScoringSystem):
    """
    사용자 개인화 기반 스코어링 시스템 (Soft Boosting 적용)
    기존 RestaurantScoringSystem을 상속받아 개인화 로직을 추가합니다.
    """
    def __init__(self, data_dir: str, user_profile: Dict):
        super().__init__(data_dir)
        # 이미 로드된 싱글톤이 있다면 데이터를 공유하거나 다시 로드
        # 여기서는 안전하게 다시 로드 (또는 싱글톤 패턴 활용 가능하나 독립성 유지)
        self.load_public_datasets()
        
        self.user_profile = user_profile
        # DB 구조: preference_weights -> themes (Dict[str, float])
        self.weights = user_profile.get("preference_weights", {}).get("themes", {})
        
        # [New] 실시간 세션 테마 가중치
        self.session_weights = {}
        
        # Hyperparameters for Soft Boosting
        self.MAX_BOOST = 2.0  # 개인화로 얻을 수 있는 최대 가산점 (+/-)

    def set_session_themes(self, themes: List[str]):
        """현재 세션(대화)에서 도출된 테마 설정"""
        self.session_weights = {theme: 1.0 for theme in themes}

    def calculate_preference_score(self, place_tags: List[str]) -> float:
        """
        Soft Boosting 알고리즘: 태그 가중치 합을 Tanh 함수로 정규화
        편향 방지: 같은 pref_tag가 여러 place_tags와 중복 매칭되는 것을 방지
        """
        if not self.weights and not self.session_weights:
            return 0.0

        raw_score = 0.0

        # 1. Long-term Profile Weights (중복 매칭 방지)
        matched_prefs = set()
        for tag in place_tags:
            for pref_tag, weight in self.weights.items():
                if pref_tag not in matched_prefs and (pref_tag in tag or tag in pref_tag):
                    raw_score += weight
                    matched_prefs.add(pref_tag)

        # 2. Session Context Weights (Real-time Boost, 중복 매칭 방지)
        matched_session = set()
        for tag in place_tags:
            for session_tag in self.session_weights:
                if session_tag not in matched_session and (session_tag in tag or tag in session_tag):
                    raw_score += 2.0
                    matched_session.add(session_tag)

        # Soft Boosting: 점수가 무한정 커지지 않도록 tanh 적용
        # raw_score가 2.0이면 tanh(2.0) ~= 0.96 -> 0.96 * MAX_BOOST(2.0) = 1.92점
        soft_score = math.tanh(raw_score) * self.MAX_BOOST
        return round(soft_score, 2)

    def calculate_final_score(self, enriched_item: Dict) -> Tuple[float, Dict]:
        """
        기본 품질 점수 + 개인화 가산점 + 가격 민감도 보정
        """
        # 1. 기본 품질 점수 (Base Score) - 부모 클래스 메서드 사용
        base_score, base_breakdown = self.calculate_score(enriched_item)

        # 2. 태그 수집
        place = enriched_item.get("place", {})
        types = place.get("types", [])
        llm_keywords = enriched_item.get("llm_keywords", [])

        # Vector DB에서 가져온 키워드도 태그로 활용
        place_keywords = place.get("keywords", {})
        keyword_tags = []
        for v in place_keywords.values():
            if isinstance(v, str) and v:
                keyword_tags.append(v)
            elif isinstance(v, list):
                keyword_tags.extend([str(item) for item in v if item])

        all_tags = types + llm_keywords + keyword_tags

        # 3. 개인화 가산점 계산
        preference_boost = self.calculate_preference_score(all_tags)

        # 4. 가격 민감도 보정 (price_sensitivity)
        price_sensitivity = self.user_profile.get("preference_weights", {}).get("price_sensitivity", 0.5)
        price_level = place.get("price_level", "")

        price_adjustment = 0.0
        if price_sensitivity >= 0.7:
            # 가격에 민감한 사용자: 비싼 곳 페널티, 저렴한 곳 보너스
            if price_level in ("PRICE_LEVEL_EXPENSIVE", "PRICE_LEVEL_VERY_EXPENSIVE"):
                price_adjustment = -0.5
            elif price_level == "PRICE_LEVEL_INEXPENSIVE":
                price_adjustment = 0.3
        elif price_sensitivity <= 0.3:
            # 가격에 둔감한 사용자: 고급 레스토랑 약간 보너스
            if price_level in ("PRICE_LEVEL_EXPENSIVE", "PRICE_LEVEL_VERY_EXPENSIVE"):
                price_adjustment = 0.2

        # 5. 최종 점수 합산
        final_score = base_score + preference_boost + price_adjustment

        # 점수 내역 업데이트
        base_breakdown["preference_boost"] = preference_boost
        base_breakdown["price_adjustment"] = price_adjustment
        base_breakdown["price_sensitivity"] = price_sensitivity
        base_breakdown["final_total"] = round(final_score, 2)

        return round(final_score, 2), base_breakdown
