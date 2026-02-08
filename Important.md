# Troubleshooting & Key Fixes

---

## 1. 개인화 스코어링이 작동하지 않던 문제

**문제**: 설문에서 저장한 사용자 선호도(데이트 4.0, 맛집탐방 4.0 등)가 코스 추천에 전혀 반영되지 않음

**원인**: `chat.py`에서 Agent 호출 시 `userId`를 전달하지 않아 `scoring_node`가 DB에서 사용자 프로필을 조회하지 못함 (dead code 상태)

**해결**: Agent 호출 시 `userId` 1줄 추가 + 점진적 가중치 학습 시스템 구축 (코스 확정 +0.3, 테이스팅 만족 +0.2, PICK +0.15, SKIP -0.05)

---

## 2. 매번 같은 장소만 추천되는 문제 (Scoring Node v4 -> v5)

**문제**: 30개 테스트 결과, 동명동 292개 장소 중 츠바메/캬베츠/오보에루/호시정/비비드 5곳이 거의 모든 케이스에서 반복 추천됨

**원인**: 기존 Top-N 선택 방식이 결정적(deterministic)
- `theme_score = base_score + theme_bonus` 에서 base_score(5~10점)가 theme_bonus(0.5점)를 압도
- 점수 정렬 후 1등부터 순서대로 선택 -> 입력이 달라도 결과가 동일

**해결**: Scoring Node v5 — Weighted Sampling + Exploration Factor (`scoring_node.py`)
- 기존: 점수 1등 -> 무조건 선택 (결정적)
- 변경: 상위 10개 후보군에서 점수 비례 확률로 샘플링 (확률적)
- Exploration Noise: 점수에 0~40% 랜덤 노이즈 추가 -> 2등, 3등도 선택 가능
- 테마 보너스 4배 강화 (0.5 -> 2.0) -> 테마별 실제 차별화

---

## 3. 편향 방지 (Bias Prevention)

**문제**: 같은 테마를 반복 설문하면 가중치가 무한정 증가 (4.0 -> 5.0 -> 6.0...)

**해결**: 가중치 상한 5.0 + tanh 정규화 + 태그 중복 매칭 방지

---

## 4. 예산 하드코딩 문제

**문제**: 모든 코스의 total_budget이 "약 50,000원"으로 고정

**해결**: Google Places의 price_level 데이터를 활용한 동적 예산 계산
