import json
import os

def load_data(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_keywords_from_posts(posts):
    """필터링된 포스트들로부터 키워드 다시 집계"""
    merged = {
        "facilities": set(),
        "location": set(),
        "hours": set(),
        "menu_type": set(),
        "signature_menu": set(),
        "ambiance": set(),
        "policy": set(),
    }
    
    for post in posts:
        keywords = post.get("keywords", {})
        for category in merged.keys():
            items = keywords.get(category, [])
            if isinstance(items, list):
                merged[category].update(items)
                
    return {k: sorted(list(v)) for k, v in merged.items()}

def create_vertex_corpus(data):
    """
    Vertex AI용 코퍼스 데이터 생성
    1. 2025년 이후 포스트 필터링
    2. 메타데이터 간소화 (title, link)
    3. 상세 키워드 제거
    """
    raw_posts = data.get('posts', [])
    filtered_posts = []
    
    print(f"Total posts before filter: {len(raw_posts)}")
    
    # 1. 2025년 이후 데이터 필터링
    for post in raw_posts:
        meta = post.get('metadata', {})
        postdate = meta.get('postdate', '')
        
        # 날짜가 있고 20250101 이상인 경우만 포함
        if postdate and postdate >= '20250101':
            filtered_posts.append(post)
            
    print(f"Total posts after filter (>= 2025): {len(filtered_posts)}")
    
    # 2. 필터링된 포스트 기반으로 Summary 재계산
    # (기존 summary는 전체 데이터 기준일 수 있으므로 다시 계산하는 것이 정확함)
    merged_summary = merge_keywords_from_posts(filtered_posts)
    
    # 3. 메타데이터 간소화
    simplified_metadata = []
    for post in filtered_posts:
        meta = post.get('metadata', {})
        simplified_metadata.append({
            "title": meta.get('title', ''),
            "link": meta.get('link', '')
        })
        
    # 4. 최종 구조 생성
    result = {
        "merged_keywords_summary": merged_summary,
        "metadata": simplified_metadata,
        "source_info": {
            "original_count": len(raw_posts),
            "filtered_count": len(filtered_posts),
            "filter_criteria": "postdate >= 20250101"
        }
    }
    
    return result

def load_source_query(filepath):
    """원본 검색어(장소명) 로드"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("query")

def save_json(data, modify_filepath):
    with open(modify_filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved to {modify_filepath}")

if __name__ == "__main__":
    input_file = 'extracted_keywords.json'
    source_file = 'rss_yield_test.json'  # 쿼리(장소명) 정보가 있는 원본 파일
    output_file = 'vertex_corpus.json'
    
    data = load_data(input_file)
    place_name = load_source_query(source_file)
    
    if data:
        vertex_data = create_vertex_corpus(data)
        
        # 장소명 추가
        if place_name:
            vertex_data["place_name"] = place_name
            print(f"Added place name: {place_name}")
        else:
            vertex_data["place_name"] = "Unknown Place"
            print("Warning: Could not find place name from source file.")
            
        save_json(vertex_data, output_file)
