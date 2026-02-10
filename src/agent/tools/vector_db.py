import os
import json
import glob
import asyncio
import time
from typing import List, Dict, Any, Optional
from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

# Load env
load_dotenv()

# Configuration (Updated from test_cloud_search.py)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "jnu-rise-edu-134")
LOCATION = "asia-northeast3"
INDEX_ENDPOINT_ID = os.getenv("VERTEX_INDEX_ENDPOINT_ID", "870892374035791872")
DEPLOYED_INDEX_ID = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "main_vector2_1770339438170")
API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY") or os.getenv("GOOGLE_API_KEY")

class GCPVectorDB:
    def __init__(self):
        self.metadata_store = {}
        self.region_map = {}
        self.gu_map = {}
        self.index_endpoint = None
        self.embedding_model = None

        # Load Data & Connect
        self._load_local_data()
        self._init_connection()

    def _load_local_data(self):
        """
        vector_data/ 폴더의 모든 키워드 파일에서 장소 메타데이터를 로드합니다.
        지원 형식: extracted_keywords_*.json (동구), kw_*.json (남구/광산구/북구/서구)
        """
        data_map = {}
        region_map = {}
        gu_map = {}

        # 파일명 prefix → 구 이름 매핑
        gu_name_map = {
            "namgu": "남구", "bukgu": "북구", "seogu": "서구",
            "gwangsan": "광산구", "donggu": "동구"
        }

        # vector_data/ 폴더 경로 결정
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        base_dir = os.path.join(project_root, "vector_data")
        if not os.path.isdir(base_dir):
            base_dir = "vector_data"

        print(f"[VectorDB] [Load] Loading from {base_dir}...")

        file_patterns = [
            os.path.join(base_dir, "extracted_keywords_*.json"),
            os.path.join(base_dir, "kw_*.json"),
        ]

        loaded_files = 0
        for pattern in file_patterns:
            for filepath in sorted(glob.glob(pattern)):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)

                    region_raw = content.get('region', '')
                    filename = os.path.basename(filepath)

                    # region/gu 이름 결정
                    if '_' in region_raw and region_raw.split('_', 1)[0] in gu_name_map:
                        prefix, region_name = region_raw.split('_', 1)
                        gu_name = gu_name_map[prefix]
                    else:
                        region_name = region_raw or filename.replace("extracted_keywords_", "").replace(".json", "")
                        gu_name = "동구"

                    for p in content.get('places', []):
                        name = p.get('place_name')
                        if not name:
                            continue
                        data_map[name] = {
                            "keywords": p.get('keywords', {}),
                            "place_name": name,
                            "region": region_name,
                            "gu": gu_name,
                        }
                        region_map[name] = region_name
                        gu_map[name] = gu_name

                    loaded_files += 1
                except Exception as e:
                    print(f"[VectorDB] [WARN] Failed to load {filepath}: {e}")

        self.metadata_store = data_map
        self.region_map = region_map
        self.gu_map = gu_map
        print(f"[VectorDB] [OK] Loaded {loaded_files} files, {len(self.metadata_store)} places.")

    def _init_connection(self):
        """Initialize connection to Vertex AI"""
        if not INDEX_ENDPOINT_ID:
            print("[VectorDB] [ERROR] VERTEX_INDEX_ENDPOINT_ID not set. GCP Search will fail.")
            return

        try:
            # 1. Init Vertex AI
            aiplatform.init(project=PROJECT_ID, location=LOCATION)
            
            # 2. Connect to Endpoint
            self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=INDEX_ENDPOINT_ID
            )
            print(f"[VectorDB] [OK] Connected to Index Endpoint: {INDEX_ENDPOINT_ID}")

            # 3. Init Embedding Model
            # test_cloud_search.py에서 사용한 gemini-embedding-001 사용
            if API_KEY:
                self.embedding_model = GoogleGenerativeAIEmbeddings(
                    model="models/gemini-embedding-001", 
                    google_api_key=API_KEY,
                    task_type="retrieval_query"
                )
                print("[VectorDB] [OK] Embedding Model Initialized (gemini-embedding-001)")
            else:
                print("[VectorDB] [ERROR] API Key missing. Cannot generate embeddings.")
        
        except Exception as e:
            print(f"[VectorDB] [ERROR] Connection Initialization Failed: {e}")

    async def search(self, query: str, k: int = 10, region_filter: str = None) -> List[Dict[str, Any]]:
        """
        Search the Vector DB for similar places with client-side filtering.
        (test_cloud_search.py 로직 반영)
        
        Args:
            query: Search text
            k: Number of final results to return
            region_filter: Optional region name for filtering (e.g., "동명동")
        """
        if not self.index_endpoint or not self.embedding_model:
            print("[VectorDB] [WARN] Service not initialized. Returning empty.")
            return []

        try:
            t0 = time.time()
            
            # 1. Generate Embedding
            query_vector = await self.embedding_model.aembed_query(query)
            t1 = time.time()

            # 2. Execute Search with High Limit
            # DB에 꼬리표가 잘못 붙어있으므로, 일단 많이(2000개) 가져와서 코드에서 거릅니다.
            SEARCH_LIMIT = 2000
            
            print(f"[VectorDB] [SEARCH] Search executing... (Limit: {SEARCH_LIMIT}, Filter: {region_filter})")
            
            # Running sync call in thread pool
            # Note: client-side filtering means we don't pass 'filter' to find_neighbors
            response = await asyncio.to_thread(
                self.index_endpoint.find_neighbors,
                deployed_index_id=DEPLOYED_INDEX_ID,
                queries=[query_vector],
                num_neighbors=SEARCH_LIMIT
            )
            t2 = time.time()

            if not response:
                return []

            raw_results = response[0]
            filtered_results = []
            
            # 3. Client-side Filtering
            for res in raw_results:
                place_id = res.id

                # Filter 1: Region Check (구 단위 or 권역 단위)
                if region_filter:
                    place_region = self.region_map.get(place_id, "")
                    place_gu = self.gu_map.get(place_id, "")
                    # "남구", "북구" 등 구 단위 필터 → gu_map으로 확인
                    # "동명동", "수완권" 등 권역 필터 → region_map으로 확인
                    if region_filter in ("동구", "남구", "북구", "서구", "광산구"):
                        if place_gu != region_filter:
                            continue
                    else:
                        if place_region != region_filter:
                            continue

                # Filter 2: Content Existence Check
                # 메타데이터(키워드)가 존재하는지 확인
                place_info = self.metadata_store.get(place_id, {})
                keywords = place_info.get('keywords', {})
                
                has_content = False
                if keywords:
                    for v in keywords.values():
                        if v: # 값이 있는 리스트가 하나라도 있으면 OK
                            has_content = True
                            break
                
                if not has_content:
                    continue # 설명 없으면 결과에서 제외
                
                # Add to results
                item = place_info.copy()
                item['similarity_score'] = res.distance
                item['id'] = place_id
                # Ensure place_name is set
                if 'place_name' not in item:
                    item['place_name'] = place_id
                    
                filtered_results.append(item)
                
                # Stop if we have enough results
                if len(filtered_results) >= k:
                    break
            
            t3 = time.time()
            
            embed_time = t1 - t0
            search_time = t2 - t1
            filter_time = t3 - t2
            total_time = t3 - t0
            
            print(f"[VectorDB] [TIMING] Total: {total_time:.2f}s (Embed: {embed_time:.2f}s, Search: {search_time:.2f}s, Filter: {filter_time:.2f}s)")
            print(f"[VectorDB] [OK] Found {len(filtered_results)} valid items for '{query}' (after filtering)")
            return filtered_results

        except Exception as e:
            print(f"[VectorDB] [ERROR] Search Failed: {e}")
            return []

# Singleton Instance
vector_db = GCPVectorDB()
