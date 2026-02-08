"""
배치 요약 생성기 - extracted_keywords → 자연어 요약
Gemini 3 Flash를 사용하여 키워드 데이터를 벡터 임베딩에 최적화된 자연어 요약으로 변환합니다.

사용법:
    python batch_generate_summaries.py

출력:
    place_summaries_동명동.json
    place_summaries_시내권.json
    place_summaries_조대권.json
"""

import json
import os
import time
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

# ============ Configuration ============
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")

MODEL_NAME = "gemini-2.0-flash"
BATCH_SIZE = 10

# 입력/출력 파일 매핑
SOURCE_FILES = {
    "동명동": "extracted_keywords_동명동.json",
    "시내권": "extracted_keywords_시내권.json",
    "조대권": "extracted_keywords_조대권.json",
}

# ============ Prompt ============
BATCH_SUMMARY_PROMPT = """당신은 광주광역시 장소 정보를 간결하게 요약하는 전문가입니다.
아래 장소들의 키워드 데이터를 각각 자연어 요약문으로 변환해주세요.

## 규칙
1. 각 장소당 2~4문장으로 요약
2. 장소명을 문장 첫머리에 포함
3. 메뉴 유형, 대표 메뉴, 분위기, 위치, 특징 등 핵심 사실만 포함
4. 주관적 평가(맛있다, 좋다, 최고 등) 절대 금지
5. 키워드가 비어있는 카테고리는 무시
6. 벡터 검색에 잘 걸리도록 구체적인 단어를 사용 (예: "한식" → "한식 전문점", "모밀" → "모밀/소바 전문점")

## 출력 형식 (반드시 JSON 배열로)
[
  {{"place_name": "가게명1", "summary": "요약문1"}},
  {{"place_name": "가게명2", "summary": "요약문2"}}
]

## 장소 데이터
{places_json}
"""


def load_places(filepath: str) -> List[Dict[str, Any]]:
    """extracted_keywords JSON에서 키워드가 있는 장소만 로드"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    places = []
    for p in data.get("places", []):
        keywords = p.get("keywords", {})
        # 키워드가 하나라도 있는 장소만
        has_content = any(
            isinstance(v, list) and len(v) > 0 for v in keywords.values()
        )
        if has_content:
            places.append(p)

    return places


def create_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        max_output_tokens=4096,
    )


def prepare_batch_input(places: List[Dict]) -> str:
    """배치용 입력 데이터 구성 (place_name + keywords만)"""
    batch = []
    for p in places:
        batch.append({
            "place_name": p["place_name"],
            "keywords": p.get("keywords", {}),
        })
    return json.dumps(batch, ensure_ascii=False, indent=2)


def parse_llm_response(response_text: str) -> List[Dict]:
    """LLM 응답에서 JSON 배열 파싱"""
    text = response_text.strip()

    # markdown 코드블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄(```json)과 마지막 줄(```) 제거
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # [ ] 범위만 추출 시도
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        print(f"  [WARN] JSON 파싱 실패. 응답 일부: {text[:200]}")
        return []


def process_batch(llm: ChatGoogleGenerativeAI, batch: List[Dict], batch_num: int, total_batches: int) -> List[Dict]:
    """단일 배치 처리"""
    places_json = prepare_batch_input(batch)
    prompt = BATCH_SUMMARY_PROMPT.format(places_json=places_json)

    place_names = [p["place_name"] for p in batch]
    print(f"  [{batch_num}/{total_batches}] 처리 중: {', '.join(place_names[:3])}{'...' if len(place_names) > 3 else ''}")

    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            results = parse_llm_response(response.content)

            if results:
                print(f"  [{batch_num}/{total_batches}] -> {len(results)}개 요약 생성 완료")
                return results
            else:
                print(f"  [{batch_num}/{total_batches}] 빈 결과, 재시도 {attempt + 1}/{max_retries}")

        except Exception as e:
            print(f"  [{batch_num}/{total_batches}] 오류: {e}")
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"    {wait}초 대기 후 재시도...")
                time.sleep(wait)

    # 모든 재시도 실패 시 빈 결과 반환
    print(f"  [{batch_num}/{total_batches}] 최종 실패. 스킵합니다.")
    return []


def process_region(llm: ChatGoogleGenerativeAI, region: str, filepath: str):
    """하나의 지역 파일 전체 처리"""
    print(f"\n{'='*60}")
    print(f"[{region}] 처리 시작: {filepath}")
    print(f"{'='*60}")

    places = load_places(filepath)
    print(f"[{region}] 키워드 있는 장소: {len(places)}개")

    if not places:
        print(f"[{region}] 처리할 장소 없음. 스킵.")
        return

    # 배치 분할
    batches = [places[i : i + BATCH_SIZE] for i in range(0, len(places), BATCH_SIZE)]
    total_batches = len(batches)
    print(f"[{region}] 총 {total_batches}개 배치 (배치 크기: {BATCH_SIZE})")

    all_summaries = []
    failed_places = []
    t0 = time.time()

    for batch_idx, batch in enumerate(batches, 1):
        results = process_batch(llm, batch, batch_idx, total_batches)

        # 결과를 place_name 기준으로 매칭
        result_map = {r["place_name"]: r["summary"] for r in results}

        for p in batch:
            name = p["place_name"]
            summary = result_map.get(name)
            if summary:
                all_summaries.append({
                    "place_name": name,
                    "region": region,
                    "summary": summary,
                    "keywords": p.get("keywords", {}),
                })
            else:
                failed_places.append(name)

        # Rate limit: 배치 간 대기
        if batch_idx < total_batches:
            time.sleep(2)

    elapsed = time.time() - t0

    # 출력 파일 저장
    output_file = f"place_summaries_{region}.json"
    output = {
        "region": region,
        "metadata": {
            "model": MODEL_NAME,
            "total_input": len(places),
            "total_output": len(all_summaries),
            "failed_count": len(failed_places),
            "elapsed_seconds": round(elapsed, 1),
            "batch_size": BATCH_SIZE,
        },
        "places": all_summaries,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[{region}] 완료!")
    print(f"  - 성공: {len(all_summaries)}개")
    print(f"  - 실패: {len(failed_places)}개")
    if failed_places:
        print(f"  - 실패 목록: {', '.join(failed_places[:10])}{'...' if len(failed_places) > 10 else ''}")
    print(f"  - 소요 시간: {elapsed:.1f}초")
    print(f"  - 저장: {output_file}")


def main():
    print("=" * 60)
    print("  배치 요약 생성기 (extracted_keywords -> 자연어 요약)")
    print(f"  모델: {MODEL_NAME} | 배치 크기: {BATCH_SIZE}")
    print("=" * 60)

    llm = create_llm()
    print("LLM 초기화 완료\n")

    for region, filepath in SOURCE_FILES.items():
        if not os.path.exists(filepath):
            print(f"[WARN] 파일 없음: {filepath} -> 스킵")
            continue
        process_region(llm, region, filepath)

    print(f"\n{'='*60}")
    print("모든 지역 처리 완료!")
    print("출력 파일:")
    for region in SOURCE_FILES:
        out = f"place_summaries_{region}.json"
        if os.path.exists(out):
            with open(out, "r", encoding="utf-8") as f:
                data = json.load(f)
            cnt = len(data.get("places", []))
            print(f"  {out}: {cnt}개 장소")
    print("=" * 60)


if __name__ == "__main__":
    main()
