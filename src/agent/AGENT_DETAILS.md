# Agent System 전체 코드 분석 문서

> 이 문서는 `src/agent/` 및 `src/mini_agent/`의 **모든 소스 코드**를 한 줄씩 분석하여 정리한 것입니다.

---

## 목차

1. [전체 구조 개요](#1-전체-구조-개요)
2. [Main Agent (`src/agent/`)](#2-main-agent-srcagent)
   - [2.1 그래프 파이프라인](#21-그래프-파이프라인)
   - [2.2 AgentState 정의](#22-agentstate-정의)
   - [2.3 Config](#23-config)
   - [2.4 노드 상세](#24-노드-상세)
     - [2.4.1 QueryPlannerNode](#241-queryplannernode)
     - [2.4.2 VectorRetrievalNode](#242-vectorretrievalnode)
     - [2.4.3 KeywordRetrievalNode](#243-keywordretrievalnode)
     - [2.4.4 EnrichmentNode](#244-enrichmentnode)
     - [2.4.5 NaverBlogSearchNode](#245-naverblogsearchnode)
     - [2.4.6 ScoringNode](#246-scoringnode)
     - [2.4.7 CourseGenerationNode (1/2/3)](#247-coursegenerationnode-123)
     - [2.4.8 AggregatorNode](#248-aggregatornode)
   - [2.5 보조 노드 (현재 그래프 미사용)](#25-보조-노드-현재-그래프-미사용)
   - [2.6 스코어링 시스템](#26-스코어링-시스템)
   - [2.7 Tools](#27-tools)
   - [2.8 진입점 (main.py)](#28-진입점-mainpy)
3. [Mini Agent (`src/mini_agent/`)](#3-mini-agent-srcmini_agent)
   - [3.1 개요](#31-개요)
   - [3.2 MiniAgent (노드 기반)](#32-miniagent-노드-기반)
   - [3.3 MiniAgentFC (Tool Calling 기반)](#33-miniagentfc-tool-calling-기반)
   - [3.4 지원 모듈](#34-지원-모듈)
4. [데이터 흐름 요약](#4-데이터-흐름-요약)
5. [외부 API 의존성](#5-외부-api-의존성)
6. [환경 변수 목록](#6-환경-변수-목록)

---

## 1. 전체 구조 개요

프로젝트는 두 개의 에이전트 시스템으로 구성됩니다.

| 구분 | Main Agent (`src/agent/`) | Mini Agent (`src/mini_agent/`) |
|------|--------------------------|-------------------------------|
| 프레임워크 | LangGraph (StateGraph) | LangChain + 직접 구현 |
| 용도 | **코스 추천** (3개 테마별 코스 생성) | **단일 장소 정보 조회** (간결 요약) |
| 파이프라인 | 8개 노드, 병렬 Fan-Out/Fan-In | 2개 노드 (검색 -> 요약) |
| 검색 방식 | Parallel Hybrid RAG (Vector + Keyword) | Google Places API 단독 또는 VectorDB |
| LLM | Google Gemini (Structured Output / Batch Scoring) | Google Gemini (자유 텍스트 응답) |

---

## 2. Main Agent (`src/agent/`)

### 2.1 그래프 파이프라인

`graph.py`의 `create_agent_graph()` 함수가 LangGraph `StateGraph`를 빌드합니다.

```
START
  |
  v
query_planner_node            <-- 테마 3개 선정 + 검색 쿼리 생성
  | (Fan-Out: Parallel Retrieval)
  |--- vector_retrieval_node    <-- Vector DB 시맨틱 검색
  '--- keyword_retrieval_node   <-- Google Places Text Search
         | (Fan-In: Merge & Enrich)
         v
      enrichment_node            <-- 후보 통합 + 상세 정보 조회
         |
         v (Conditional Edge)
      +- run_blog_search == True --> naver_blog_search_node -+
      '- run_blog_search != True ----------------------------'
         |
         v
      scoring_node               <-- LLM 배치 채점 + 공공데이터 + 개인화 + 코스 생성
         | (Fan-Out: Parallel Generation)
         |--- generate_course_1
         |--- generate_course_2
         '--- generate_course_3
                | (Fan-In: Aggregate)
                v
            aggregator_node      <-- 결과 취합 + 최종 JSON 포맷팅
                |
                v
               END
```

**핵심 설계 원칙:**
- **2단계 Fan-Out/Fan-In**: Retrieval Phase (Vector + Keyword 병렬) -> Generation Phase (코스 3개 병렬)
- **Conditional Edge**: `run_blog_search` 플래그에 따라 Naver 블로그 검색을 조건부 실행
- **Reducer Pattern**: `generated_courses` 필드는 `operator.add` reducer를 사용하여 병렬 노드의 결과를 자동 합산

---

### 2.2 AgentState 정의

`state.py` -- `TypedDict` 기반의 에이전트 상태 스키마입니다.

| 필드 | 타입 | Reducer | 설명 |
|------|------|---------|------|
| `messages` | `Sequence[BaseMessage]` | `add_messages` | 대화 메시지 히스토리 (자동 누적) |
| `current_step` | `str` | 덮어쓰기 | 현재 실행 단계 (`"thinking"`, `"tool_calling"`, `"responding"`) |
| `tool_results` | `dict | None` | 덮어쓰기 | 도구 실행 결과 |
| `query_plan` | `dict | None` | 덮어쓰기 | QueryPlanner가 생성한 검색 계획 |
| `vector_candidates` | `list | None` | 덮어쓰기 | Vector DB 검색 결과 (시맨틱) |
| `keyword_candidates` | `list | None` | 덮어쓰기 | Keyword 검색 결과 (Google Places) |
| `place_data` | `list | None` | 덮어쓰기 | Google Places API 결과 (레거시) |
| `enriched_results` | `list | None` | 덮어쓰기 | 통합 데이터 (`{place, blogs}` 리스트) |
| `scored_results` | `list | None` | 덮어쓰기 | 스코어링 완료된 결과 |
| `final_answer` | `str | None` | 덮어쓰기 | 최종 JSON 응답 문자열 |
| `survey_data` | `dict | None` | 덮어쓰기 | 사용자 설문 데이터 (성별, 연령, 테마, 동행인, 지역 등) |
| `themes` | `list[str] | None` | 덮어쓰기 | QueryPlanner가 생성한 3가지 테마 |
| `generated_courses` | `list` | `operator.add` | 병렬 생성된 코스 리스트 (합산) |
| `userId` | `str | None` | 덮어쓰기 | 사용자 ID (개인화 스코어링용) |
| `run_blog_search` | `bool | None` | 덮어쓰기 | Naver 블로그 검색 실행 여부 |

---

### 2.3 Config

`config.py` -- 환경 변수 기반 설정 클래스입니다.

| 설정 | 환경 변수 | 기본값 | 용도 |
|------|----------|--------|------|
| `GOOGLE_API_KEY` | `GOOGLE_API_KEY` | `""` | Gemini LLM + Embedding API 키 |
| `GEMINI_MODEL` | `GEMINI_MODEL` | `"gemini-3-flash-preview"` | 사용할 Gemini 모델명 |
| `LANGSMITH_TRACING` | `LANGSMITH_TRACING` | `"false"` | LangSmith 트레이싱 활성화 여부 |
| `LANGSMITH_API_KEY` | `LANGSMITH_API_KEY` | `""` | LangSmith API 키 |
| `LANGSMITH_PROJECT` | `LANGSMITH_PROJECT` | `"default"` | LangSmith 프로젝트 이름 |
| `MAX_ITERATIONS` | `MAX_ITERATIONS` | `10` | 에이전트 최대 반복 횟수 |
| `VERBOSE` | `VERBOSE` | `true` | 상세 로그 출력 여부 |

모듈 임포트 시점에 `config.enable_langsmith()`가 자동 실행되어 LangSmith 환경 변수를 설정합니다.

---

### 2.4 노드 상세

#### 2.4.1 QueryPlannerNode

**파일**: `nodes/query_planner_node.py`

**역할**: 사용자 질문을 분석하여 **3가지 추천 테마**와 **Google Places 검색 쿼리**를 생성합니다.

**동작 방식**:
1. 마지막 사용자 메시지와 `survey_data`(성별, 연령, 테마 선호, 동행인, 선호 지역)를 수집합니다.
2. `ChatGoogleGenerativeAI`에 **Structured Output** (`with_structured_output(QueryPlan)`)을 사용하여 정해진 스키마로 응답을 강제합니다.
3. 프롬프트에서 테마 이름은 **2~4글자 이내 핵심 명사**만 허용하고, 지역명/수식어/문장형을 금지합니다.
4. 사용자 질문에 특정 지역이 명시되지 않은 경우, `survey_data`의 선호 지역을 기준으로 쿼리를 생성합니다.

**출력 스키마 (`QueryPlan` Pydantic 모델)**:
```python
class QueryPlan(BaseModel):
    themes: list[str]          # 3가지 테마 키워드 (예: ["힐링", "데이트", "맛집"])
    place_queries: list[str]   # Google Places 검색 쿼리 (최대 3개)
    result_count: int          # 쿼리당 검색 결과 개수 (기본 20, 최대 20)
    reasoning: str             # 테마 선정 이유
```

**State 업데이트**: `query_plan`, `themes`

**실패 시 Fallback**: 기본 테마 `["맛집", "카페", "힐링"]` 반환.

---

#### 2.4.2 VectorRetrievalNode

**파일**: `nodes/vector_search_node.py`

**역할**: GCP Vertex AI Vector Search를 사용하여 **시맨틱(의미적) 유사도** 기반으로 장소 후보를 검색합니다.

**동작 방식**:
1. `query_plan.place_queries`를 입력 쿼리로 사용합니다 (없으면 `themes`를 fallback).
2. `survey_data.region`을 지역 필터로 적용합니다 ("광주 전체", "모름", "상관없음"은 필터 해제).
3. 중복 쿼리를 `set()`으로 제거한 후 `vector_db.search(q, k=20, region_filter=...)` 를 **병렬(`asyncio.gather`)** 실행합니다.
4. 결과를 `id` 또는 `place_name` 기준으로 중복 제거합니다.

**의존성**: `src/agent/tools/vector_db.py`의 싱글톤 `vector_db` 인스턴스 사용.

**State 업데이트**: `vector_candidates`

---

#### 2.4.3 KeywordRetrievalNode

**파일**: `nodes/keyword_search_node.py`

**역할**: **Google Places Text Search API**를 사용하여 키워드 매칭 기반으로 장소 후보를 검색합니다.

**동작 방식**:
1. `query_plan.place_queries`를 검색어로 사용합니다.
2. `aiohttp.ClientSession`으로 Google Places API (`places:searchText`)를 비동기 호출합니다.
3. **최소한의 필드만 요청** (비용 최적화):
   ```
   places.name, places.displayName, places.formattedAddress,
   places.location, places.priceLevel, places.types
   ```
4. 쿼리당 최대 10개, 전체적으로 `places/{PLACE_ID}` 기준 중복 제거.
5. `_search_places_async()`에서 timeout 10초 설정.

**State 업데이트**: `keyword_candidates`

---

#### 2.4.4 EnrichmentNode

**파일**: `nodes/enrichment_node.py`

**역할**: Vector Search와 Keyword Search의 후보군을 **병합(Merge) + 중복 제거(Dedup) + 상세 정보 조회(Enrich)** 합니다.

**Phase 1 -- Merge & Deduplicate**:
1. **Keyword 후보 처리**: `places/{PLACE_ID}` 형태의 Google ID를 이미 보유 -> `candidates_map`에 `{google_id, name, source: "keyword"}` 형태로 추가.
2. **Vector 후보 처리**:
   - `google_place_id`가 있으면 Google ID로 매핑.
   - 같은 ID가 이미 Keyword에서 들어와 있으면 `source: "hybrid"`로 업데이트.
   - Google ID가 없으면 이름 기반 매칭 시도 -> 매칭 실패 시 `TEMP_{name}` 키로 임시 등록.
3. 양쪽 모두에서 발견된 장소는 `source: "hybrid"`로 표시.

**Phase 2 -- Details Fetching (최적화)**:
1. 최대 **30개** 후보로 제한 (`MAX_ENRICH = 30`).
2. `_fetch_place_with_resolution()` 함수로 **ID Resolution + Details Fetch를 단일 병렬 작업으로 통합**:
   - Google ID가 없으면 -> `_resolve_place_id_async()`로 Text Search하여 ID 획득 -> 그 다음 Details Fetch.
   - Google ID가 있으면 -> 바로 `_get_place_details_async()` 호출.
3. `asyncio.gather`로 모든 후보를 동시 처리.
4. 상세 정보 요청 필드:
   ```
   id, name, displayName, formattedAddress, addressComponents, location,
   rating, userRatingCount, priceLevel,
   reviews.originalText, reviews.text, reviews.rating, reviews.relativePublishTimeDescription,
   photos.name
   ```

**Phase 3 -- 후처리**:
1. **주소 정규화** (`_normalize_formatted_address()`):
   - "대한민국", "Republic of Korea", "South Korea" 등 국가 prefix 제거.
   - `addressComponents`가 있으면 한국식 행정구역 순서(`시 -> 구 -> 동 -> 도로`)로 재구성.
2. **이름 한글화** (`_normalize_names_to_korean_async()`):
   - 한글이 포함되지 않은 식당 이름 감지 (`re.search(r'[가-힣]')`).
   - Gemini LLM에게 "한국인이 검색하는 한글 표기"로 변환 요청.
   - JSON 배열로 파싱하여 이름 교체.
3. **ScoringNode 호환 형식으로 래핑**: `{"place": {...}, "blogs": []}`.

**State 업데이트**: `enriched_results`

---

#### 2.4.5 NaverBlogSearchNode

**파일**: `nodes/naver_blog_search.py`

**역할**: 네이버 블로그 검색을 통해 각 장소의 블로그 리뷰를 수집합니다.

**현재 상태**: **바이패스(pass-through)** -- 실제 Naver API 호출 없이 `enriched_results`를 그대로 반환합니다. Conditional Edge로 `run_blog_search == True`일 때만 실행됩니다.

**향후 구현 시**: 각 `enriched_results[i]['place']['name']`으로 Naver 검색 후 `blogs` 배열에 추가하는 로직이 주석으로 안내되어 있습니다.

**State 업데이트**: `enriched_results` (변경 없이 통과)

---

#### 2.4.6 ScoringNode

**파일**: `nodes/scoring_node.py`

**역할**: `enriched_results`를 입력으로 받아 **LLM 배치 채점 + 공공데이터 가산 + 개인화 부스팅**을 수행하고, **코스까지 직접 생성**합니다.

##### LLM 채점 시스템 (v4)

4가지 차원에서 직접 점수를 매깁니다:

| 차원 | 범위 | 평가 기준 예시 |
|------|------|--------------|
| **맛 (taste)** | 0~2점 | 2.0: "인생맛집", "JMT" / 1.5: "맛있다" / 1.0: "무난" / 0.5: "별로" / 0.0: "최악" |
| **서비스/분위기 (service)** | 0~2점 | 2.0: "감성 터짐" / 1.5: "친절" / 1.0: "보통" / 0.5: "불친절" / 0.0: "최악" |
| **가성비 (value)** | 0~1점 | 1.0: "가성비 갑" / 0.5: "적당" / 0.0: "비쌈" |
| **재방문 (revisit)** | 0~1점 | 1.0: "또 갈 것" / 0.5: "기회 되면" / 0.0: "안 갈 것" |

**배치 처리**: 5개씩 묶어서 하나의 LLM 호출로 처리 (JSON 리스트 출력). `asyncio.gather`로 배치들을 병렬 실행.

**프롬프트 구성**: 각 장소의 Google 리뷰(최대 5개, 150자 제한) + 블로그 리뷰(최대 3개, 300자 제한) + Vector 메타데이터(`menu_type`, `signature_menu`, `ambiance` 등)를 포함하여 LLM이 JSON 형식으로 점수를 출력하도록 요청합니다.

**총점 계산**:
```
총점 = 기본 품질 점수(공공데이터) + LLM 감성 점수 + [개인화 가산점]
```

##### 개인화 스코어링

- `userId`가 있으면 MongoDB에서 사용자 프로필(`preference_weights.themes`)을 조회.
- 세션 테마(`themes`)도 `set_session_themes()`으로 실시간 반영.
- `PersonalizedScoringSystem.calculate_final_score()` -> `calculate_preference_score()`에서 **Soft Boosting** (tanh 정규화) 적용.

##### 코스 생성 통합 (LLM 없이 규칙 기반)

Scoring Node 내부에서 테마별 키워드 매칭으로 코스를 직접 생성합니다:

1. **테마-키워드 매핑 테이블**:
   ```
   "데이트" -> ["데이트", "분위기", "로맨틱", "감성", "커플"]
   "맛집"   -> ["맛집", "맛있", "인생맛집", "JMT", "존맛"]
   "카페"   -> ["카페", "디저트", "커피", "베이커리"]
   "디저트" -> ["디저트", "케이크", "빙수", "달콤"]
   "뷰맛집" -> ["뷰", "전망", "야경", "통유리", "탁트인"]
   "힐링"   -> ["힐링", "조용", "편안", "휴식"]
   "가성비" -> ["가성비", "저렴", "푸짐", "합리적"]
   ```
2. 각 테마마다 `base_score + theme_bonus`로 정렬하여 Top N(기본 4개) 장소를 선택.
3. `used_place_ids` set으로 코스 간 장소 중복 방지.
4. 각 장소의 `reason` 필드에 감성 분석 요약 + 테마 맥락 문구를 조합.
5. 장소 타입은 `_infer_place_type()`으로 키워드/이름 기반 추론 ("카페"/"베이커리"/"식당").

**State 업데이트**: `scored_results`, `generated_courses`

---

#### 2.4.7 CourseGenerationNode (1/2/3)

**파일**: `nodes/course_generation_node.py`

**역할**: 병렬로 실행되는 3개의 코스 생성 노드입니다. 각 노드는 할당된 테마에 맞춰 하나의 코스를 LLM으로 생성합니다.

**현재 동작**: Scoring Node에서 이미 코스를 생성한 경우 (`generated_courses`가 존재하면) **스킵**합니다.

```python
# generate_course_1 / 2 / 3 모두 동일한 패턴
if state.get("generated_courses"):
    print("[Course Gen N] Scoring에서 이미 생성됨 - 스킵")
    return {"generated_courses": []}  # 빈 리스트 반환 (reducer에 영향 없음)
```

**LLM 사용 시 동작 (`_generate_single_course`)**:
1. `scored_results`에서 상위 30개 장소를 컨텍스트(`_format_place_data`)로 구성합니다.
2. 각 장소의 ID, 이름, 주소, 평점, 리뷰 수, 종합점수, 인증 정보, 블로그 요약(100자)을 포함합니다.
3. 테마, `places_per_course`(설문 기반, 기본 4개), **Diversity Strategy** 지침을 프롬프트에 포함합니다.
4. **Diversity Strategy**: 단순 점수 상위가 아니라 테마 적합성을 우선 고려하도록 명시.
5. 코스 제목은 **6글자 이내**로 제한.
6. Gemini LLM에게 JSON 형식의 단일 코스를 생성하도록 요청합니다.
7. `course_id`를 강제 주입하여 Aggregator에서의 정렬을 보장합니다.

**State 업데이트**: `generated_courses` (리스트에 append -- `operator.add` reducer)

---

#### 2.4.8 AggregatorNode

**파일**: `nodes/aggregator_node.py`

**역할**: `generated_courses` 리스트를 취합하여 최종 JSON 응답을 생성합니다.

**동작 방식**:
1. `generated_courses`를 `course_id` 기준으로 정렬 (1, 2, 3 순서 보장). `course_id`가 없는 코스는 99로 처리하여 뒤로 배치.
2. 최종 응답 구조를 생성합니다:
   ```json
   {
     "answer": "3가지 테마의 맞춤형 코스를 추천해 드립니다.",
     "recommended_courses": [
       { "course_id": 1, "course_name": "...", "course_description": "...", "places": [...], "total_budget": "..." },
       { "course_id": 2, ... },
       { "course_id": 3, ... }
     ]
   }
   ```
3. `json.dumps(ensure_ascii=False, indent=2)`로 직렬화하여 `final_answer`에 저장합니다.
4. 코스가 없을 경우: `"코스를 생성하는 데 실패했습니다."` 메시지 반환.

**State 업데이트**: `final_answer`, `current_step = "responding"`

---

### 2.5 보조 노드 (현재 그래프 미사용)

아래 노드들은 코드로 존재하지만 현재 `graph.py`의 파이프라인에서는 **연결되지 않습니다**.

#### LLMNode (`nodes/llm_node.py`)
- Gemini LLM을 호출하여 응답을 생성하는 **범용 노드**.
- `scored_results` 또는 `enriched_results`를 `SystemMessage`로 주입하여 3개 코스를 JSON으로 생성하도록 요청.
- `search_tool`을 바인딩하여 도구 호출 기능도 보유.
- 컨텍스트 예산: `MAX_CONTEXT_CHARS = 50,000`.
- 리뷰는 800자, 블로그는 5,000자로 제한.
- 각 장소에 임시 ID (`p1`, `p2`...) 부여.
- 가격대를 기호(원)로 변환하여 표시.

#### ToolNode (`nodes/tool_node.py`)
- LangGraph 내장 `ToolNode`를 사용하여 `search_tool` 실행을 담당.
- LLM이 도구 호출을 요청했을 때 실행되는 보조 노드.
- `tool_executor.ainvoke(state)` -> `messages`에 `ToolMessage` 추가.

#### GooglePlaceSearchNode (`nodes/google_place_search.py`)
- Google Places API를 직접 호출하여 장소 검색 + 리뷰 수집을 수행하는 **레거시 노드**.
- **Hybrid Search 지원**: Vector DB 결과를 추가 검색 쿼리로 활용. Vector 결과의 `id`를 장소 이름으로 사용하여 `"{region} {place_name}"` 형식의 쿼리를 추가 (최대 5개).
- 주소 정규화(`_normalize_formatted_address`), 이름 한글 변환(`_normalize_names_to_korean_async`) 기능 포함.
- 리뷰 3개 샘플링, 사진 첫 번째만 추출.
- 현재는 EnrichmentNode + KeywordRetrievalNode로 대체됨.

#### PublicDataSearchNode (`nodes/public_data_node.py`)
- 로컬 JSON 파일(`data/gwangju_food_list.json`)에서 광주 맛집 리스트를 로드.
- `json.load()`로 직접 파싱 (Pandas 미사용, 경량).
- JSON 구조: 리스트 형태 또는 `"data"` 키 안에 리스트가 있는 형태 모두 지원.
- Scoring 시스템의 "공공데이터 인증 맛집 가산점"에 활용 목적.

#### TourismRelationNode (`nodes/tourism_relation_node.py`)
- 한국관광공사 빅데이터 API (`TarRlteTarService1/searchKeyword1`)를 호출하여 연관 관광지 정보를 검색.
- 조회 기준 연월: 현재로부터 **4개월 전** (API 데이터 업데이트 주기 고려).
- 반환 필드: 연관 관광지 이름(`rlteTatsNm`), 중분류(`rlteCtgryMclsNm`), 순위(`rlteRank`).
- `REFERENCE_API_` 환경 변수로 디코딩 키를 설정.
- `requests.get()` 사용 (동기 호출).

---

### 2.6 스코어링 시스템

**파일**: `scoring_system.py`

두 개의 클래스로 구성됩니다:

#### RestaurantScoringSystem (기본)

**공공 데이터 로드**:
- `data/Gwangju City Certified Exemplary Restaurant.json` -> 모범 음식점 목록
- `data/gwangju_food_list.json` -> 광주 맛집 리스트

**점수 산출 방식**:

| 항목 | 최대 점수 | 계산 방법 |
|------|----------|----------|
| 모범 음식점 인증 | +1점 | 이름 정확 매칭 또는 유사도 90% 이상(`SequenceMatcher`) + 동일 구/동 |
| 광주 맛집 선정 | +1점 | 이름 정확 매칭 또는 유사도 90% 이상 + 동일 구/동 |
| 블로그 언급 | 0점 | 제거됨 (편향 방지 -- 사용자 피드백 반영) |
| Google 평점 | +2점 | `(rating / 5.0) * 2` |
| Google 리뷰 수 | +2점 | `min(2.0, log10(count + 1) * 0.5)` (로그 스케일) |

**이름 정규화** (`normalize_name()`): 공백/탭 제거, 괄호 안 내용 제거 (예: `"고려조삼계탕 (상무점)"` -> `"고려조삼계탕"`), 특수문자 제거, 소문자 변환.

**주소에서 구/동 추출** (`extract_district()`): `"광주광역시 서구 치평동 ..."` -> `"서구 치평동"`. 동/읍/면 suffix를 감지.

**싱글톤 패턴**: `get_scoring_system(data_dir)` 함수로 인스턴스를 한 번만 생성하여 재사용.

#### PersonalizedScoringSystem (개인화 -- 상속)

`RestaurantScoringSystem`을 상속받아 **Soft Boosting** 알고리즘을 추가합니다.

**Soft Boosting 알고리즘**:
```
raw_score = SUM(Long-term Profile Weights) + SUM(Session Context Weights * 2.0)
soft_score = tanh(raw_score) * MAX_BOOST(2.0)
최종 점수 = 기본 품질 점수 + soft_score
```

- **Long-term Profile Weights**: DB에 저장된 사용자 선호 태그 가중치 (`preference_weights.themes`). 태그 부분 매칭 (`pref_tag in tag or tag in pref_tag`)으로 유연하게 매칭.
- **Session Context Weights**: 현재 대화에서 QueryPlanner가 도출한 테마. 실시간 반영을 위해 가중치 **2.0** 부여.
- **tanh 정규화**: 점수가 무한정 커지는 것을 방지.
  - 예: `raw_score=2.0` -> `tanh(2.0)=0.964` -> `0.964 * 2.0 = 1.93점`
- 태그 소스: Google Types + LLM 키워드를 장소 태그로 사용하여 사용자 선호와 교차 매칭.

---

### 2.7 Tools

#### search_tool (`tools/search.py`)
- `@tool` 데코레이터로 정의된 웹 검색 **플레이스홀더**.
- 현재는 **미구현** -- `"'{query}'에 대한 검색 결과: 검색 API를 연동해주세요."` 메시지만 반환.
- LLMNode와 ToolNode에서 참조되지만, 현재 그래프에서는 사용되지 않음.
- 향후 Tavily, DuckDuckGo 등 연동 예정 (TODO 주석).

#### GCPVectorDB (`tools/vector_db.py`)
- **GCP Vertex AI Matching Engine**을 사용하는 벡터 검색 도구.
- 모듈 로드 시점에 싱글톤 인스턴스 `vector_db`가 초기화됨.

**초기화 과정 (`__init__`)**:
1. **로컬 메타데이터 로드** (`_load_local_data`):
   - `extracted_keywords_동명동.json`, `extracted_keywords_시내권.json`, `extracted_keywords_조대권.json` 파일에서 장소별 키워드 정보 로드.
   - `metadata_store`: `{장소이름: {keywords, summary, place_name, region}}` 딕셔너리.
   - `region_map`: `{장소이름: 지역명}` 딕셔너리 (파일명 기반 지역 매핑).
2. **Vertex AI 연결** (`_init_connection`):
   - `aiplatform.init(project=PROJECT_ID, location="asia-northeast3")`.
   - `MatchingEngineIndexEndpoint(index_endpoint_name=INDEX_ENDPOINT_ID)` 연결.
3. **임베딩 모델 초기화**:
   - `GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", task_type="retrieval_query")`.

**검색 과정 (`search` 메서드)**:
1. 쿼리를 `aembed_query()`로 임베딩 벡터로 변환 (비동기).
2. Vertex AI에서 **2,000개** 이웃을 검색 (`asyncio.to_thread`로 동기 호출을 비동기 래핑).
   - DB에 메타데이터 태그가 불완전하므로 많이 가져와서 코드에서 필터링하는 전략.
3. **클라이언트 사이드 필터링**:
   - **지역 필터**: `region_map`에서 장소의 실제 지역과 요청된 `region_filter` 비교.
   - **컨텐츠 필터**: `metadata_store`의 `keywords` 딕셔너리에 값이 있는 항목만 통과.
4. `similarity_score = res.distance`를 결과에 포함.
5. 요청된 `k`개에 도달하면 조기 종료.
6. 타이밍 정보 출력 (Embedding / Search / Filter 각각 소요 시간).

**설정값**:
| 설정 | 기본값 |
|------|--------|
| `PROJECT_ID` | `"jnu-rise-edu-134"` |
| `LOCATION` | `"asia-northeast3"` |
| `INDEX_ENDPOINT_ID` | `"870892374035791872"` |
| `DEPLOYED_INDEX_ID` | `"main_vector2_1770339438170"` |

---

### 2.8 진입점 (`main.py`)

**`run_agent(user_input: str) -> str`** (비동기):
1. `config.validate()` -- `GOOGLE_API_KEY` 존재 확인.
2. `create_agent_graph()` -- 전체 그래프 생성 및 컴파일.
3. 초기 상태 설정:
   ```python
   {
       "messages": [HumanMessage(content=user_input)],
       "current_step": "thinking",
       "tool_results": None, "query_plan": None,
       "place_data": None, "enriched_results": None, "final_answer": None,
   }
   ```
4. `graph.ainvoke(initial_state)` -- 비동기 실행.
5. `result["final_answer"]` 반환 (없으면 `"응답을 생성하지 못했습니다."`).

**`main()`**: CLI 인터페이스 -- `input()` 루프로 사용자 입력을 받아 `asyncio.run(run_agent(...))`을 실행. `"quit"`, `"exit"`, `"종료"` 입력으로 종료.

**패키지 export**: `from src.agent import create_agent_graph, AgentState`

**`app` 인스턴스**: `graph.py` 하단에서 `app = create_agent_graph()` 로 모듈 레벨 인스턴스를 생성하여 외부에서 바로 사용 가능.

---

## 3. Mini Agent (`src/mini_agent/`)

### 3.1 개요

Main Agent의 **간소화 버전**입니다. 코스 추천이 아닌 **단일 장소 정보 조회 및 간결 요약**을 목적으로 합니다. 두 가지 구현이 존재합니다:

| 구분 | MiniAgent | MiniAgentFC |
|------|-----------|-------------|
| 아키텍처 | 노드 기반 (직접 파이프라인) | LangChain AgentExecutor |
| 도구 호출 | 코드에서 직접 호출 | LLM이 Tool Calling으로 자동 결정 |
| LLM 역할 | 요약 생성만 | 도구 호출 결정 + 응답 생성 |
| 추적 | `@traceable` 데코레이터 | AgentExecutor `verbose=True` |

---

### 3.2 MiniAgent (노드 기반)

**파일**: `mini_agent.py`

**파이프라인**:
```
Step 1: PlaceSearchNode.search(query, max_places)    <-- Google Places API 검색
Step 2: LLMNode.generate_summary(query, places)      <-- Gemini 요약 생성
```

**반환 형식**:
```python
{
    "query": "검색 쿼리",
    "places": [장소 정보 리스트],
    "enriched_data": [{"place": p, "blogs": []}],
    "answer": "LLM이 생성한 요약"
}
```

**LangSmith 추적**: `@traceable` 데코레이터로 `MiniAgent.run`, `MiniAgent.PlaceSearch`, `MiniAgent.LLMSummary` 각각 추적.

**동기/비동기 지원**: `run_async(query)` (비동기) + `run(query)` (동기 래퍼, `asyncio.run` 사용).

**편의 함수**: `run_mini_agent(query)` -- `MiniAgent`를 생성하고 바로 실행.

---

### 3.3 MiniAgentFC (Tool Calling 기반)

**파일**: `mini_agent_fc.py`

**아키텍처**: LangChain `AgentExecutor` + `create_tool_calling_agent`를 사용합니다.

**도구 정의**:
- `search_google_places`: `StructuredTool.from_function`으로 생성된 동기 도구.
- 내부적으로 `place_search.search_places()`의 동기 래퍼(`asyncio.get_event_loop().run_until_complete`)를 사용.
- 결과를 간결한 JSON 문자열 (이름, 주소, 평점, 리뷰 수)로 반환.

**시스템 프롬프트**:
```
당신은 친절한 장소 추천 전문가입니다.
사용자가 장소를 물어보면 search_google_places 도구를 사용해서 검색하세요.
검색 결과를 바탕으로 간결하게 3줄 이내로 요약해주세요.
반드시 이모지를 포함해서 친근하게 응답하세요.
```

**AgentExecutor 설정**: `verbose=True`, `handle_parsing_errors=True`, temperature `0.7`.

---

### 3.4 지원 모듈

#### Config (`config.py`)
Main Agent와 동일한 구조이지만 추가 설정:
- `GOOGLE_CLOUD_API_KEY`: Google Places API 전용 키.
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET`: Naver 블로그 검색 API 인증.
- `validate()`: `GOOGLE_API_KEY`와 `GOOGLE_CLOUD_API_KEY` 모두 필수.

#### PlaceSearchNode (`nodes/place_search_node.py`)
- `place_search.search_places(query, max_places)`를 래핑하는 클래스.
- LangSmith 추적을 위한 독립 노드.
- 에러 발생 시 빈 리스트 반환.

#### LLMNode (`nodes/llm_node.py`)
- 장소 정보를 컨텍스트로 구성하여 Gemini에게 **불릿 포인트 3개 이하**의 간결한 요약을 생성하도록 요청.
- **컨텍스트 구성 우선순위**:
  - VectorDB 키워드(`menu_type`, `signature_menu`, `ambiance`)가 있으면 우선 사용.
  - 없으면 Google Places 리뷰(2개, 80자 제한)를 사용.
- 각 불릿은 **15자 이내**, 이모지 1개 포함.
- LangSmith run name: `"MiniAgent_LLM_Summary"`.

#### VectorSearchNode (`nodes/vector_search_node.py`)
- GCPVectorDB를 **지연 로딩(lazy loading)** 방식으로 초기화 (`_get_vector_db()`).
- `search(query, max_places, region_filter)` 메서드로 VectorDB 검색 수행.
- 결과를 표준 장소 정보 형식으로 변환:
  ```python
  {
      "id": "...", "name": "...", "address": "...",
      "rating": 0, "total_reviews": 0, "lat": 0, "lng": 0,
      "keywords": {...}, "menu_type": "...", "signature_menu": [...],
      "ambiance": [...], "special_features": [...], "recommended_for": [...],
      "similarity_score": 0.95
  }
  ```
- 에러 발생 시 traceback 출력 후 빈 리스트 반환.

#### Place Search (`place_search.py`)
- Google Places Text Search API + Place Details API를 비동기로 호출.
- `search_places(query, max_results)`:
  1. `_search_places_async()`: Text Search로 장소 목록 획득 (필드: `displayName, formattedAddress, location, priceLevel`).
  2. `_get_place_details_async()`: 각 장소의 상세 정보 병렬 수집 (필드: `rating, userRatingCount, reviews, photos`).
  3. 데이터 병합: `{id, name, address, lat, lng, rating, total_reviews, photo_name, reviews}`.
  4. 리뷰 상위 3개만 포함.

#### Blog Search (`blog_search.py`)
- Naver 블로그 검색 API + RSS 매칭으로 블로그 본문을 수집.
- `enrich_places_with_blogs(places)`: 여러 장소에 대해 병렬 블로그 검색 수행.
- **RSS 매칭 로직** (`_search_and_match_rss`):
  1. Naver 검색 API로 **100개** 블로그 결과 획득 (`display=100`, `sort=date`).
  2. 각 블로그 링크에서 `blog_id`와 `logNo`를 파싱 (`_parse_blog_link`).
  3. `naver.me` 단축 링크는 `_resolve_shortlink()`로 최대 3번 리다이렉트를 따라가 원본 URL 해석.
  4. `https://rss.blog.naver.com/{blog_id}.xml`에서 RSS 피드를 `feedparser`로 파싱 (캐싱 적용).
  5. RSS 엔트리와 `logNo` 매칭.
  6. 매칭된 항목에서 HTML 태그를 제거한 본문(`full_content`)을 추출.
  7. 최대 **5개** 매칭 결과 반환 (`RSS_MAX_MATCH = 5`).
- **장소별 검색 쿼리**: `"{지역명} {장소이름}"` 형식 (주소에서 시/구/동 추출).

---

## 4. 데이터 흐름 요약

```
[사용자 입력 + survey_data]
        |
        v
  QueryPlannerNode ---------> themes: ["힐링", "데이트", "맛집"]
        |                     place_queries: ["광주 동명동 카페", ...]
        |
   +----+----+
   v         v
Vector    Keyword
Search    Search
   |         |
   +----+----+
        v
  EnrichmentNode ----------> enriched_results: [
        |                      { place: {name, address, rating, lat, lng,
        |                                reviews, photo_name, keywords, source},
        |                        blogs: [] }
        |                    ]
        v
  (NaverBlogSearch) -------> blogs 데이터 추가 (현재 pass-through)
        |
        v
  ScoringNode -------------> scored_results: [{..., score: 7.5, score_breakdown: {
        |                       taste: 1.5, service: 2.0, value: 0.5, revisit: 1.0,
        |                       exemplary: 1, gwangju_food: 0, rating: 1.6, reviews: 0.9,
        |                       sentiment: 5.0, preference_boost: 1.5, ...
        |                     }}]
        |                     generated_courses: [course1, course2, course3]
        |
   +----+----+
   v    v    v
 Gen1  Gen2  Gen3 ----------> (스킵 -- 이미 생성됨)
   |    |    |
   +----+----+
        v
  AggregatorNode ----------> final_answer: JSON 문자열
                               {
                                 "answer": "3가지 테마의 맞춤형 코스를...",
                                 "recommended_courses": [
                                   { "course_id": 1, "course_name": "힐링 코스",
                                     "course_description": "...",
                                     "places": [
                                       { "id": "p1", "name": "...", "type": "식당",
                                         "lat": 35.0, "lng": 126.0, "reason": "..." }
                                     ],
                                     "total_budget": "약 50,000원" },
                                   { "course_id": 2, ... },
                                   { "course_id": 3, ... }
                                 ]
                               }
```

---

## 5. 외부 API 의존성

| API | 용도 | 사용 위치 |
|-----|------|----------|
| **Google Gemini API** | LLM 호출 (Structured Output, 배치 채점, 코스 생성, 이름 변환, 요약) | QueryPlanner, ScoringNode, CourseGen, EnrichmentNode, LLMNode |
| **Google Gemini Embedding API** | 쿼리 임베딩 벡터 생성 (`gemini-embedding-001`) | GCPVectorDB |
| **GCP Vertex AI Matching Engine** | 벡터 유사도 검색 (find_neighbors) | VectorRetrievalNode |
| **Google Places API (New)** | Text Search, Place Details (리뷰, 평점, 사진) | KeywordRetrievalNode, EnrichmentNode, GooglePlaceSearchNode, PlaceSearchNode |
| **Naver 블로그 검색 API** | 블로그 검색 (100개) | MiniAgent BlogSearch |
| **Naver Blog RSS** | 블로그 본문 수집 (feedparser) | MiniAgent BlogSearch |
| **한국관광공사 API** | 연관 관광지 조회 (TarRlteTarService1) | TourismRelationNode (현재 미사용) |
| **LangSmith** | 트레이싱/모니터링 | Config에서 전역 설정 |

---

## 6. 환경 변수 목록

| 변수명 | 필수 | 용도 |
|--------|------|------|
| `GOOGLE_API_KEY` | O | Gemini LLM + Embedding API 키 |
| `GOOGLE_CLOUD_API_KEY` | O | Google Places API + Embedding 대체 키 |
| `GOOGLE_CLOUD_PROJECT` | O | GCP 프로젝트 ID (기본: `jnu-rise-edu-134`) |
| `GEMINI_MODEL` | X | Gemini 모델명 (기본: `gemini-3-flash-preview`) |
| `VERTEX_INDEX_ENDPOINT_ID` | O | Vertex AI Vector Index Endpoint ID |
| `VERTEX_DEPLOYED_INDEX_ID` | O | 배포된 Vector Index ID |
| `NAVER_CLIENT_ID` | X | Naver 블로그 검색 API Client ID |
| `NAVER_CLIENT_SECRET` | X | Naver 블로그 검색 API Client Secret |
| `REFERENCE_API_` | X | 한국관광공사 API 디코딩 키 |
| `LANGSMITH_TRACING` | X | LangSmith 트레이싱 활성화 (`true`/`false`) |
| `LANGSMITH_API_KEY` | X | LangSmith API 키 |
| `LANGSMITH_ENDPOINT` | X | LangSmith 엔드포인트 (기본: `https://api.smith.langchain.com`) |
| `LANGSMITH_PROJECT` | X | LangSmith 프로젝트 이름 (기본: `default`) |
| `MAX_ITERATIONS` | X | 에이전트 최대 반복 (기본: `10`) |
| `VERBOSE` | X | 상세 로그 출력 (기본: `true`) |
