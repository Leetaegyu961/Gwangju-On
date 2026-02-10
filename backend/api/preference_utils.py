"""
Preference Learning Utilities
사용자 행동(PICK, SKIP, 코스 확정, 테이스팅 노트)에 따라
선호도 가중치를 점진적으로 업데이트하는 헬퍼 함수.
"""

from datetime import datetime

# 가중치 범위 제한 (편향 방지)
WEIGHT_MAX = 5.0
WEIGHT_MIN = 0.0


async def increment_preference(db, user_id: str, tag: str, delta: float):
    """
    특정 태그의 선호도 가중치를 점진적으로 업데이트합니다.

    - 상한: 5.0 (아무리 좋아해도 5.0을 넘지 않음)
    - 하한: 0.0 (음수가 되지 않음)
    - tanh 정규화가 스코어링 시점에서 적용되므로,
      5.0과 3.0의 실제 가산점 차이는 매우 작음 (편향 방지)

    Args:
        db: MongoDB database instance
        user_id: 사용자 ID
        tag: 선호도 태그 (예: "맛집", "카페", "데이트")
        delta: 가중치 변화량 (양수=강화, 음수=약화)
    """
    if not tag or not user_id:
        return

    tag = tag.strip()
    if not tag:
        return

    pref = await db["user_preferences"].find_one({"userId": user_id})
    current_weights = {}
    if pref:
        current_weights = pref.get("preference_weights", {}).get("themes", {})

    current = current_weights.get(tag, 0.0)
    new_value = max(WEIGHT_MIN, min(WEIGHT_MAX, current + delta))
    current_weights[tag] = round(new_value, 2)

    await db["user_preferences"].update_one(
        {"userId": user_id},
        {"$set": {
            "preference_weights.themes": current_weights,
            "last_updated": datetime.now().isoformat()
        }},
        upsert=True
    )

    if abs(delta) >= 0.1:
        print(f"📊 [Preference] {user_id}: '{tag}' {current:.2f} → {new_value:.2f} (delta={delta:+.2f})")


async def learn_from_course_selection(db, user_id: str, course_places: list):
    """
    코스 확정 시 해당 코스의 장소 카테고리/태그로부터 선호도를 학습합니다.
    증분: +0.3 per tag

    Args:
        db: MongoDB database instance
        user_id: 사용자 ID
        course_places: 코스에 포함된 장소 리스트 (dict)
    """
    DELTA = 0.3
    seen_tags = set()

    for place in course_places:
        place_type = place.get("type", "")
        place_tags = place.get("tags", [])

        for tag in [place_type] + place_tags:
            if tag and tag not in seen_tags:
                seen_tags.add(tag)
                await increment_preference(db, user_id, tag, DELTA)

    if seen_tags:
        print(f"📚 [Preference Learning] Course selection: {len(seen_tags)} tags updated for {user_id}")


async def learn_from_tasting_note(db, user_id: str, satisfaction: int, session_themes: list,
                                   atmosphere: str = None, best_place_id: str = None):
    """
    테이스팅 노트의 만족도, 분위기, 베스트 장소를 기반으로 선호도를 학습합니다.

    학습 항목:
    1. satisfaction → 세션 테마 가중치 조정 (4-5: +0.2, 1-2: -0.1)
    2. atmosphere → 분위기 선호 태그 강화 (+0.3)
    3. best_place_id → 해당 장소의 카테고리 태그 강화 (+0.4)

    Args:
        db: MongoDB database instance
        user_id: 사용자 ID
        satisfaction: 만족도 (1-5)
        session_themes: 해당 세션의 테마 리스트
        atmosphere: 분위기 선호 (예: "quiet", "lively", "romantic")
        best_place_id: 최고 장소 ID 또는 이름
    """
    # 1. 만족도 기반 테마 가중치 조정 (기존 로직)
    if satisfaction >= 4:
        delta = 0.2
    elif satisfaction <= 2:
        delta = -0.1
    else:
        delta = 0  # 만족도 3은 테마 변화 없음

    if delta != 0:
        for theme in session_themes:
            if theme:
                await increment_preference(db, user_id, theme, delta)

    # 2. 분위기 선호 학습
    ATMOSPHERE_TAG_MAP = {
        "quiet": "조용한",
        "lively": "활기찬",
        "romantic": "로맨틱",
        "casual": "캐주얼",
        "cozy": "아늑한",
        "trendy": "트렌디",
        "traditional": "전통적인",
    }
    if atmosphere:
        tag = ATMOSPHERE_TAG_MAP.get(atmosphere)
        if tag:
            await increment_preference(db, user_id, tag, 0.3)
            print(f"🎨 [Preference Learning] Atmosphere '{atmosphere}' → '{tag}' +0.3 for {user_id}")

    # 3. 베스트 장소 카테고리 학습
    if best_place_id:
        try:
            pool_session = await db["refinement_sessions"].find_one({"userId": user_id})
            if pool_session:
                for place in pool_session.get("refinement_pool", []):
                    if place.get("id") == best_place_id or place.get("name") == best_place_id:
                        place_type = place.get("type", "")
                        if place_type:
                            await increment_preference(db, user_id, place_type, 0.4)
                            print(f"⭐ [Preference Learning] Best place type '{place_type}' +0.4 for {user_id}")
                        # 장소의 tags도 학습
                        for tag in place.get("tags", [])[:3]:
                            if tag:
                                await increment_preference(db, user_id, tag, 0.2)
                        break
        except Exception as e:
            print(f"⚠️ [Preference Learning] Best place lookup failed: {e}")

    learned_count = len(session_themes) + (1 if atmosphere else 0) + (1 if best_place_id else 0)
    if learned_count > 0:
        print(f"📝 [Preference Learning] Tasting note (satisfaction={satisfaction}): {learned_count} signals processed for {user_id}")


async def learn_from_discovery_action(db, user_id: str, action: str, category: str):
    """
    Discovery 화면에서의 PICK/SKIP/REJECT 행동에 따라 선호도를 미세 조정합니다.
    PICK: +0.15, SKIP/REJECT: -0.05

    Args:
        db: MongoDB database instance
        user_id: 사용자 ID
        action: "PICK", "SKIP", "REJECT"
        category: 장소 카테고리
    """
    if not category:
        return

    if action == "PICK":
        await increment_preference(db, user_id, category, 0.15)
    elif action in ("SKIP", "REJECT"):
        await increment_preference(db, user_id, category, -0.05)
