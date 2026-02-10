"""
Course Modifier
의도 분석 결과에 따라 코스를 규칙 기반으로 수정합니다. (LLM 호출 없음, 즉시 실행)
"""

import json
import math
import random
from typing import Optional, List, Dict, Tuple
from .intent_analyzer import RefinementIntent


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 직선 거리(km)"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _proximity_bonus(dist_km: float) -> float:
    """거리 기반 보너스/페널티 (코스 내 장소 간 왔다갔다 방지)"""
    if dist_km <= 2.0:
        return 2.0
    elif dist_km <= 5.0:
        return 0.0
    elif dist_km <= 10.0:
        return -2.0
    else:
        return -4.0


def find_replacement(
    pool: list,
    current_place: dict,
    criteria: str,
    required_type: str = "",
    used_ids: set = None,
    course_places: list = None
) -> Optional[dict]:
    """후보 풀에서 조건에 맞는 대체 장소를 찾습니다.
    course_places가 주어지면 코스 내 다른 장소들과의 거리를 고려합니다."""
    if used_ids is None:
        used_ids = set()

    # 코스 중심점 계산 (거리 보너스/페널티용)
    centroid = None
    if course_places:
        valid = [p for p in course_places if p.get("lat") and p.get("lng")]
        if valid:
            centroid = (
                sum(p["lat"] for p in valid) / len(valid),
                sum(p["lng"] for p in valid) / len(valid),
            )

    candidates = []
    cur_id = current_place.get("id") or current_place.get("name")

    for p in pool:
        pid = p.get("id") or p.get("name")
        if pid in used_ids or pid == cur_id:
            continue

        # 타입 필터
        if required_type and p.get("type", "") != required_type:
            continue

        score = p.get("score", 0)
        bonus = 0

        # 키워드 매칭
        if criteria:
            kw = p.get("keywords", {})
            name = p.get("name", "")
            all_text = f"{name} {json.dumps(kw, ensure_ascii=False)}".lower()
            if criteria.lower() in all_text:
                bonus += 2

        # 거리 보너스/페널티
        if centroid and p.get("lat") and p.get("lng"):
            dist = _haversine_km(centroid[0], centroid[1], p["lat"], p["lng"])
            bonus += _proximity_bonus(dist)

        candidates.append((p, score + bonus + random.uniform(0, 1)))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1], reverse=True)
    top = candidates[:5]
    weights = [max(s, 0.1) for _, s in top]
    total = sum(weights)
    probs = [w / total for w in weights]
    return random.choices([p for p, _ in top], weights=probs, k=1)[0]


def find_by_direction(
    pool: list,
    current_place: dict,
    direction: str,
    used_ids: set = None
) -> Optional[dict]:
    """현재 장소 기준으로 특정 방향에 있는 장소를 찾습니다."""
    if used_ids is None:
        used_ids = set()

    cur_lat = current_place.get("lat", 0)
    cur_lng = current_place.get("lng", 0)
    cur_id = current_place.get("id") or current_place.get("name")

    if not cur_lat or not cur_lng:
        return None

    candidates = []
    for p in pool:
        pid = p.get("id") or p.get("name")
        if pid in used_ids or pid == cur_id:
            continue

        p_lat = p.get("lat", 0)
        p_lng = p.get("lng", 0)
        if not p_lat or not p_lng:
            continue

        match = False
        if direction in ("north", "위", "위쪽", "북쪽"):
            match = p_lat > cur_lat
        elif direction in ("south", "아래", "아래쪽", "남쪽"):
            match = p_lat < cur_lat
        elif direction in ("east", "오른쪽", "동쪽"):
            match = p_lng > cur_lng
        elif direction in ("west", "왼쪽", "서쪽"):
            match = p_lng < cur_lng

        if match:
            dist = math.sqrt((p_lat - cur_lat)**2 + (p_lng - cur_lng)**2)
            candidates.append((p, dist))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1])
    return random.choice(candidates[:3])[0]


def _build_place(p: dict, slot_idx: int, reason: str, place_type: str = "") -> dict:
    """후보 장소를 코스 장소 형식으로 변환합니다. (photo_name 포함)"""
    import os
    photo_name = p.get("photo_name")
    api_url = os.getenv("API_URL", "http://localhost:8000")
    img_url = f"{api_url}/api/photo?name={photo_name}" if photo_name else None

    return {
        "id": f"p{slot_idx+1}",
        "name": p.get("name", "알 수 없음"),
        "type": place_type or p.get("type", "식당"),
        "lat": p.get("lat", 0),
        "lng": p.get("lng", 0),
        "reason": reason,
        "photo_name": photo_name,
        "img": img_url,
    }


def _get_used_ids(courses: list) -> set:
    """전체 코스에서 사용 중인 장소 ID를 수집합니다."""
    used = set()
    for c in courses:
        for p in c.get("places", []):
            used.add(p.get("id") or p.get("name"))
    return used


def apply_modification(
    courses: list,
    pool: list,
    intent: RefinementIntent
) -> Tuple[list, str]:
    """의도에 따라 코스를 수정하고 변경 요약을 반환합니다."""
    ci = intent.course_idx
    si = intent.slot_idx

    if ci < 0 or ci >= len(courses):
        return courses, "코스를 찾을 수 없어요."

    course = courses[ci]
    places = course.get("places", [])
    used_ids = _get_used_ids(courses)

    # 교체 대상을 제외한 나머지 장소 목록 (거리 계산용)
    other_places = [p for idx, p in enumerate(places) if idx != si]

    if intent.action == "swap":
        if si < 0 or si >= len(places):
            si = 0
        old = places[si]
        other_places = [p for idx, p in enumerate(places) if idx != si]
        rep = find_replacement(pool, old, intent.criteria, old.get("type", ""), used_ids, course_places=other_places)
        if rep:
            places[si] = _build_place(rep, si, f"'{intent.criteria}' 조건으로 변경" if intent.criteria else "새로운 장소로 변경", old.get("type", ""))
            return courses, f"'{old.get('name','?')}'→'{rep.get('name','?')}'(으)로 변경했어요!"
        return courses, "대체 장소를 찾지 못했어요."

    elif intent.action == "remove":
        if si < 0 or si >= len(places):
            si = len(places) - 1
        removed = places.pop(si)
        return courses, f"'{removed.get('name','?')}'을 제거했어요."

    elif intent.action == "add":
        add_type = intent.new_type or "식당"
        rep = find_replacement(pool, {}, intent.criteria, add_type, used_ids, course_places=places)
        if rep:
            places.append(_build_place(rep, len(places), "추가 요청으로 선정", add_type))
            return courses, f"'{rep.get('name','?')}'을 추가했어요!"
        return courses, "추가할 장소를 찾지 못했어요."

    elif intent.action == "shift_location":
        if si < 0 or si >= len(places):
            si = 0
        old = places[si]
        direction = intent.direction or "east"
        rep = find_by_direction(pool, old, direction, used_ids)
        if rep:
            places[si] = _build_place(rep, si, f"더 {direction}쪽 장소로 변경", old.get("type", ""))
            return courses, f"'{old.get('name','?')}'→'{rep.get('name','?')}'({direction}쪽)로 변경!"
        return courses, f"{direction}쪽에 적합한 장소가 없어요."

    elif intent.action == "change_type":
        if si < 0 or si >= len(places):
            si = 0
        old = places[si]
        new_type = intent.new_type or "카페"
        other_places = [p for idx, p in enumerate(places) if idx != si]
        rep = find_replacement(pool, old, intent.criteria, new_type, used_ids, course_places=other_places)
        if rep:
            places[si] = _build_place(rep, si, f"{new_type}(으)로 변경", new_type)
            return courses, f"'{old.get('name','?')}'→'{rep.get('name','?')}'({new_type})로 변경!"
        return courses, f"{new_type} 타입 장소를 찾지 못했어요."

    elif intent.action == "change_theme":
        new_places = []
        local_used = set()
        changed = 0
        for i, old in enumerate(places):
            # change_theme: 나머지 장소 기준으로 가까운 곳 우선
            remaining = [p for j, p in enumerate(places) if j != i]
            rep = find_replacement(pool, old, intent.criteria, old.get("type", ""), local_used, course_places=remaining)
            if rep:
                local_used.add(rep.get("id") or rep.get("name"))
                new_places.append(_build_place(rep, i, f"'{intent.criteria}' 분위기에 맞춰 선정", old.get("type", "")))
                changed += 1
            else:
                new_places.append(old)
        course["places"] = new_places
        return courses, f"'{intent.criteria}' 분위기로 {changed}곳을 변경했어요!"

    return courses, "요청을 이해하지 못했어요. 다시 말씀해 주세요."
