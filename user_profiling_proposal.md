# 사용자 데이터 수집 진단 및 개인화 추천 시스템 고도화 제안

## 1. 현황 정밀 분석 및 진단

### 1.1 데이터 수집 및 저장 구조 진단
현재 시스템의 코드를 분석한 결과, 데이터 수집 및 저장 방식에 있어 **"세션 단위의 단기 기억"**에 의존하고 있으며, **"사용자 단위의 장기 기억 및 프로파일링"** 구조가 부재함이 확인되었습니다.

| 분석 항목 | 현황 (AS-IS) | 문제점 |
| :--- | :--- | :--- |
| **데이터 모델** | `UserTripSession` 내에 `SurveyData`와 `IntentContext`가 종속되어 있음. | 세션이 만료되거나 새로운 여행을 시작하면 이전 사용자의 선호 정보가 초기화됨. 사용자의 취향이 축적되지 않음. |
| **로그 수집** | `UserActivityLog`에 `PICK`, `SKIP`, `REJECT` 단순 액션만 기록됨. | *왜* 선택했는지, *무엇*을 싫어했는지에 대한 맥락 데이터(Context Data)가 부족하여 정밀한 취향 분석이 불가능함. |
| **DB 구조** | `user_trip_sessions` (세션 정보), `user_archive` (완료된 코스) 위주. | 사용자 고유의 성향(선호 태그, 기피 태그, 평균 소비 금액 등)을 관리하는 `UserProfile` 또는 `UserPreference` 컬렉션이 없음. |

### 1.2 스코어링 알고리즘 진단
현재 `src/agent/scoring_system.py`의 `RestaurantScoringSystem`은 **"객관적 품질 평가"**에 집중되어 있습니다.

*   **품질 중심:** 모범음식점 여부, 구글 평점, 리뷰 수, LLM 감성 분석(맛/서비스 등)을 통해 점수를 산출합니다.
*   **개인화 부재:** 모든 사용자에게 동일한 점수를 부여합니다. 예를 들어, "조용한 분위기"를 선호하는 사용자와 "활기찬 분위기"를 선호하는 사용자에게 동일한 랭킹을 제공합니다.

---

## 2. 데이터베이스 스키마 및 데이터 로깅 개선안

사용자의 행동 패턴을 자산화하기 위해 **장기 기억 저장소(Long-term Memory Store)** 구축이 필수적입니다.

### 2.1 신규 테이블(Collection) 설계 제안

MongoDB를 사용 중이므로, 유연한 스키마 확장이 가능합니다. `users` 컬렉션을 확장하거나 별도의 `user_preferences` 컬렉션을 신설합니다.

#### A. `UserPreferenceProfile` (사용자 성향 프로필)
사용자의 누적된 선호도를 저장하는 핵심 저장소입니다.

```json
{
  "userId": "uuid-string",
  "last_updated": "2024-05-20T10:00:00Z",
  "preference_weights": {
    // 테마별 가중치 (기본 1.0, 선호 시 > 1.0, 비선호 시 < 1.0)
    "themes": {
      "mood_quiet": 1.2,    // 조용한 분위기 선호
      "mood_trendy": 1.1,
      "food_seafood": 0.5   // 해산물 비선호
    },
    // 비용 민감도 (0.0 ~ 1.0)
    "price_sensitivity": 0.8 // 가성비를 중요하게 생각함
  },
  "behavior_stats": {
    "avg_spend_per_meal": 25000,
    "total_trips": 5,
    "most_visited_category": "korean_food"
  }
}
```

#### B. `DetailedInteractionLog` (상세 상호작용 로그)
단순 클릭을 넘어, 해당 장소의 어떤 속성이 사용자에게 노출되었을 때 반응했는지를 기록합니다.

```json
{
  "logId": "uuid",
  "userId": "uuid",
  "sessionId": "uuid",
  "targetPlaceId": "place_123",
  "action": "PICK", // PICK, CLICK_DETAIL, REJECT, TIME_DWELL
  "context_snapshot": {
    "presented_tags": ["quiet", "ocean_view", "expensive"], // 당시 노출된 태그
    "ranking_position": 3 // 리스트 내 순위
  },
  "timestamp": "..."
}
```

### 2.2 데이터 로깅 및 업데이트 파이프라인
1.  **Implicit Feedback (암시적 피드백):** 사용자가 장소를 클릭하거나 코스에 담을 때, 해당 장소가 가진 태그들의 가중치를 `UserPreferenceProfile`에서 미세하게 상향 조정 (+0.05).
2.  **Explicit Feedback (명시적 피드백):** "이곳은 너무 시끄러워요" 같은 채팅 입력 시, `mood_noisy` 태그 가중치를 대폭 하향 조정 (-0.5).
3.  **Feedback Loop:** `Analysis Agent`가 주기적으로(또는 세션 종료 시) 로그를 분석하여 프로필을 갱신합니다.

---

## 3. 개인화 추천을 위한 가중치 기반 스코어링 (Weighted Scoring) 설계

객관적 점수(Quality Score)와 주관적 점수(Preference Score)를 결합하되, **Soft Boosting**을 통해 사용자의 취향을 자연스럽게 반영하는 알고리즘입니다.

### 3.1 알고리즘 수식

$$ FinalScore = (W_q \times QualityScore) + (W_p \times PreferenceScore) $$

*   **QualityScore (기존):** 평점, 인증 여부, 리뷰 감성 (0~10점 스케일로 정규화)
*   **PreferenceScore (신규):** 사용자 성향과 장소 속성의 일치도 (0~10점)
*   **Soft Boosting Function:** 과도한 편향을 막기 위해 Sigmoid 또는 Logit 함수를 변형하여 가산점의 상한선을 둡니다.

### 3.2 코드 레벨 상세 구현 제안

`src/agent/scoring_system.py`에 통합하거나 상속하여 구현합니다.

```python
import math
from typing import Dict, List

class PersonalizedScoringSystem:
    def __init__(self, user_profile: Dict):
        """
        user_profile: DB에서 로드한 UserPreferenceProfile 데이터
        """
        self.user_profile = user_profile
        self.weights = user_profile.get("preference_weights", {}).get("themes", {})
        
        # 하이퍼파라미터
        self.ALPHA_QUALITY = 0.7   # 품질 점수 비중
        self.BETA_PREFERENCE = 0.3 # 개인화 점수 비중
        self.MAX_BOOST = 2.0       # 개인화로 받을 수 있는 최대 가산점

    def calculate_preference_score(self, place_tags: List[str]) -> float:
        """
        장소의 태그와 사용자 선호 가중치를 매칭하여 점수 계산 (Soft Boosting)
        """
        score = 0.0
        matched_count = 0
        
        for tag in place_tags:
            # 태그 가중치 조회 (기본값 0.0, 선호하면 양수, 싫어하면 음수)
            # 예: DB에는 1.2로 저장 -> 0.2 가산점 / 0.5로 저장 -> -0.5 감점 방식 등으로 변환 필요
            # 여기서는 DB에 선호도 점수(-1.0 ~ 1.0)가 저장되어 있다고 가정
            weight = self.weights.get(tag, 0.0)
            score += weight
            if weight != 0:
                matched_count += 1
        
        # Soft Boosting: 점수가 무한정 커지지 않도록 Tanh 함수 등으로 정규화 후 스케일링
        # score 범위가 -N ~ N 일 때, 이를 -MAX_BOOST ~ MAX_BOOST 로 매핑
        
        soft_score = math.tanh(score) * self.MAX_BOOST 
        return soft_score

    def calculate_final_score(self, base_score: float, place_tags: List[str]) -> Dict:
        """
        최종 점수 도출
        """
        # 1. 개인화 점수 계산 (가산점 형태)
        preference_boost = self.calculate_preference_score(place_tags)
        
        # 2. 최종 점수 합산
        # 품질 점수는 그대로 두고, 개인화 점수를 'Bonus' 개념으로 더함
        # 이렇게 하면 품질이 낮은 곳이 취향이라고 해서 1등이 되는 것을 방지하면서도,
        # 비슷한 품질이면 취향에 맞는 곳이 올라감.
        final_score = base_score + preference_boost
        
        return {
            "final_score": round(final_score, 2),
            "base_score": base_score,
            "preference_boost": round(preference_boost, 2)
        }

# --- 사용 예시 ---
# user_prefs = {"preference_weights": {"themes": {"조용한": 0.8, "해산물": -1.0}}}
# scorer = PersonalizedScoringSystem(user_prefs)
# result = scorer.calculate_final_score(base_score=4.5, place_tags=["조용한", "카페"])
# 결과: Base 4.5 + Boost (조용한 0.8 -> tanh(0.8)*2.0 ≈ 1.3) = 5.8
```

### 3.3 적용 전략 (Action Plan)

1.  **Backend API**: `/user/preference` 엔드포인트를 신설하여 프론트엔드에서 태그 선택 시 즉시 가중치를 업데이트할 수 있게 합니다.
2.  **Scoring Node**: 기존 `scoring_node.py`에서 `RestaurantScoringSystem` 대신 `PersonalizedScoringSystem`을 사용하도록 교체합니다. 이때 `state`에서 `userId`를 받아 DB에서 프로필을 조회하는 로직이 추가되어야 합니다.
3.  **SurveyScreen**: 초기 설문 결과도 일회성으로 쓰지 않고 `UserPreferenceProfile`의 초기값으로 저장합니다.
