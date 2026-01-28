"""
E2E 테스트 결과 분석 스크립트
e2e_test_results.json 파일을 읽어서 다양한 분석을 수행합니다.
"""

import json
import statistics
from collections import defaultdict


def analyze_test_results(json_file: str):
    """
    E2E 테스트 결과를 분석합니다.
    
    Args:
        json_file: 결과 JSON 파일 경로
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print("=" * 80)
    print("📊 E2E 테스트 결과 분석")
    print("=" * 80)
    
    # 1. 기본 통계
    total_tests = len(results)
    success_tests = [r for r in results if r["status"] == "success"]
    failed_tests = [r for r in results if r["status"] == "error"]
    
    print(f"\n[1] 기본 통계")
    print(f"  - 전체 테스트: {total_tests}개")
    print(f"  - 성공: {len(success_tests)}개 ({len(success_tests)/total_tests*100:.1f}%)")
    print(f"  - 실패: {len(failed_tests)}개 ({len(failed_tests)/total_tests*100:.1f}%)")
    
    if failed_tests:
        print(f"\n  ⚠️ 실패한 테스트:")
        for test in failed_tests:
            print(f"    - 시나리오 {test['scenario_id']}: {test['description']}")
            print(f"      에러: {test.get('error_message', 'Unknown')}")
    
    # 2. 점수 분포 분석
    all_scores = []
    for result in success_tests:
        for item in result.get("top_5_results", []):
            all_scores.append(item["score"])
    
    if all_scores:
        print(f"\n[2] 점수 분포 분석 (총 {len(all_scores)}개 음식점)")
        print(f"  - 평균 점수: {statistics.mean(all_scores):.2f}점")
        print(f"  - 중앙값: {statistics.median(all_scores):.2f}점")
        print(f"  - 최고 점수: {max(all_scores):.2f}점")
        print(f"  - 최저 점수: {min(all_scores):.2f}점")
        print(f"  - 표준편차: {statistics.stdev(all_scores):.2f}점")
    
    # 3. 감성 분석 점수 분포
    sentiment_scores = []
    for result in success_tests:
        for item in result.get("top_5_results", []):
            sentiment = item["score_breakdown"].get("sentiment", 0)
            if sentiment > 0:
                sentiment_scores.append(sentiment)
    
    if sentiment_scores:
        print(f"\n[3] LLM 감성 분석 점수 분포 ({len(sentiment_scores)}개)")
        print(f"  - 평균 감성 점수: {statistics.mean(sentiment_scores):.2f}점")
        print(f"  - 중앙값: {statistics.median(sentiment_scores):.2f}점")
        print(f"  - 최고: {max(sentiment_scores):.2f}점")
        print(f"  - 최저: {min(sentiment_scores):.2f}점")
    
    # 4. 가장 많이 추천된 음식점 Top 5
    restaurant_counts = defaultdict(int)
    restaurant_avg_scores = defaultdict(list)
    
    for result in success_tests:
        for item in result.get("top_5_results", []):
            name = item["name"]
            restaurant_counts[name] += 1
            restaurant_avg_scores[name].append(item["score"])
    
    print(f"\n[4] 가장 많이 추천된 음식점 Top 5")
    top_restaurants = sorted(restaurant_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for idx, (name, count) in enumerate(top_restaurants, 1):
        avg_score = statistics.mean(restaurant_avg_scores[name])
        print(f"  {idx}. {name}")
        print(f"     - 추천 빈도: {count}회")
        print(f"     - 평균 점수: {avg_score:.2f}점")
    
    # 5. 공공 데이터 인증 비율
    certified_count = 0
    total_restaurants = 0
    
    for result in success_tests:
        for item in result.get("top_5_results", []):
            total_restaurants += 1
            if item["score_breakdown"]["exemplary"] > 0 or item["score_breakdown"]["gwangju_food"] > 0:
                certified_count += 1
    
    if total_restaurants > 0:
        print(f"\n[5] 공공 데이터 인증 분석")
        print(f"  - 전체 추천 음식점: {total_restaurants}개")
        print(f"  - 인증 맛집 (모범/광주): {certified_count}개 ({certified_count/total_restaurants*100:.1f}%)")
        print(f"  - 비인증 맛집: {total_restaurants - certified_count}개 ({(total_restaurants - certified_count)/total_restaurants*100:.1f}%)")
    
    # 6. 감성 평가 요약 분석
    sentiment_summaries = defaultdict(int)
    for result in success_tests:
        for item in result.get("top_5_results", []):
            summary = item["score_breakdown"].get("sentiment_summary", "")
            if summary and summary != "분석 실패 - 기본값":
                # 키워드 추출 (간단한 분석)
                if "긍정" in summary:
                    sentiment_summaries["긍정적"] += 1
                elif "부정" in summary:
                    sentiment_summaries["부정적"] += 1
                elif "보통" in summary or "평범" in summary:
                    sentiment_summaries["보통"] += 1
                else:
                    sentiment_summaries["기타"] += 1
    
    if sentiment_summaries:
        print(f"\n[6] 감성 평가 요약 분석")
        for category, count in sorted(sentiment_summaries.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {category}: {count}개")
    
    # 7. 시나리오별 Top 1 음식점
    print(f"\n[7] 시나리오별 1위 음식점")
    for result in success_tests:
        if result.get("top_5_results"):
            top_1 = result["top_5_results"][0]
            print(f"  시나리오 {result['scenario_id']}: {result['description']}")
            print(f"    → {top_1['name']} ({top_1['score']:.2f}점)")
            print(f"       감성: {top_1['score_breakdown']['sentiment']:.1f}점 - {top_1['score_breakdown']['sentiment_summary']}")
    
    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = "e2e_test_results.json"
    
    try:
        analyze_test_results(json_file)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_file}")
        print("먼저 test_e2e_agent.py를 실행하여 결과를 생성하세요.")
    except Exception as e:
        print(f"❌ 분석 중 오류 발생: {e}")
