# Survey 시스템 내 지역명(Region Name) 데이터 처리 및 Agent 연동 아키텍처 분석

본 문서는 Survey 시스템 프론트엔드에서 수집된 지역명 데이터가 백엔드를 거쳐 AI Agent의 컨텍스트로 활용되기까지의 엔드투엔드(End-to-End) 처리 흐름을 기술적으로 분석한 보고서입니다.

## 1. 데이터 수집 및 UI 계층 (Frontend)

사용자로부터 초기 여행 선호도를 입력받는 Survey 화면에서의 지역 데이터 처리 로직입니다.

*   **관련 파일**: `frontend/screens/SurveyScreen.tsx`
*   **데이터 소스**:
    *   **Pre-defined Regions**: 코드 내 하드코딩된 지역 목록 (`regions` 배열)
        *   값: `['수완지구', '충장로', '첨단지구', '상무지구', '내 중심', '기타']`
    *   **User Input**: '기타' 선택 시 텍스트 입력 (`customRegion`), '내 중심' 선택 시 GPS 좌표.
*   **수집 로직 (`handleRegionClick`)**:
    *   **일반 지역**: 버튼 클릭 시 해당 텍스트(예: "수완지구")를 상태값으로 저장.
    *   **내 중심 (My Location)**: `navigator.geolocation`을 통해 위도/경도(Lat/Lng)를 획득.
    *   **기타 (Custom)**: 사용자가 입력한 텍스트를 그대로 사용.
*   **데이터 포맷팅**:
    *   전송 시점에 `regionStr` 변수를 생성하여 단일 문자열로 변환합니다.
    *   일반/기타: 지역명 텍스트 (예: "수완지구", "성수동")
    *   내 중심: `"위도,경도"` 포맷의 문자열 (예: "37.1234,127.5678")

## 2. 데이터 전송 및 저장 (Backend API)

프론트엔드에서 수집된 데이터가 백엔드로 전송되어 저장되는 파이프라인입니다.

*   **API 엔드포인트**: `POST /api/user/survey`
*   **관련 파일**: `backend/api/user.py`, `backend/models/user.py`
*   **페이로드 구조 (`SurveyResult` Model)**:
    ```json
    {
      "userId": "uuid-string",
      "region": "수완지구",  // 또는 "37.xxx,127.xxx"
      "courses": [...],
      "themes": ["데이트", "맛집탐방"],
      ...
    }
    ```
*   **데이터 처리 및 저장**:
    1.  **매핑 (Mapping)**: 별도의 정규화(Normalization)나 ID 매핑 테이블(예: Region ID 1 = 수완지구)을 거치지 않고, **Raw Text** 그대로 처리됩니다.
    2.  **세션 생성**: 새로운 여행 세션(`UserTripSession`)을 생성하고, `intent_context.survey_data` 필드 내에 지역 정보를 임베딩합니다.
    3.  **영구 저장**: MongoDB의 `user_trip_sessions` 컬렉션에 JSON 문서 형태로 저장됩니다.

## 3. Agent 연동 및 활용 메커니즘

저장된 지역 정보가 AI Agent의 추론 과정에 어떻게 주입(Injection)되고 활용되는지 분석합니다.

*   **Trigger**: 사용자가 채팅 메시지를 전송 (`POST /api/chat`)
*   **Context Injection**:
    *   `backend/api/chat.py`에서 사용자의 활성 세션을 조회하여 `survey_data`를 추출합니다.
    *   LangGraph Agent 실행 시 `survey_data`를 `state`의 일부로 주입합니다.
*   **Query Planning (핵심 로직)**:
    *   **관련 파일**: `src/agent/nodes/query_planner_node.py`
    *   **프롬프트 엔지니어링**: `query_planner_node`는 LLM에게 검색 계획을 요청할 때, `survey_data`에 있는 `region` 정보를 컨텍스트로 제공합니다.
    *   **검색어 생성 규칙**:
        > "중요: 사용자 질문에 특정 지역이 명시되어 있지 않다면, 반드시 [사용자 정보]의 '선호 지역'을 기준으로 검색 쿼리를 생성하세요."
    *   **동적 쿼리 생성**: 예를 들어 사용자가 "맛집 추천해줘"라고만 해도, Agent는 `region="수완지구"` 컨텍스트를 참조하여 **"수완지구 맛집"**, **"수완지구 분위기 좋은 식당"**과 같은 구체적인 검색어(`place_queries`)를 생성합니다.
*   **실행 (Execution)**:
    *   생성된 "지역명 + 키워드" 조합의 쿼리가 `google_place_search_node`로 전달되어 실제 Google Maps API 검색을 수행합니다.

## 4. 아키텍처 요약 다이어그램

```mermaid
graph TD
    User[User (Frontend)] -->|Click/Input| UI[SurveyScreen UI]
    UI -->|POST /user/survey (Raw String)| API[Backend API (FastAPI)]
    API -->|Save Session| DB[(MongoDB: user_trip_sessions)]
    
    User -->|Chat Request| ChatAPI[Chat API]
    ChatAPI -->|Fetch Context| DB
    ChatAPI -->|Inject survey_data| Agent[AI Agent (LangGraph)]
    
    subgraph "Agent Internal"
        Planner[Query Planner Node]
        Search[Google Place Search]
        Planner -->|Generate Query: 'Region + Theme'| Search
    end
    
    Agent --> Planner
```

## 5. 결론

현재 시스템은 지역 정보를 **비정형 텍스트(Raw Text)** 형태로 관리하고 있으며, 이를 **LLM의 프롬프트 컨텍스트로 직접 주입**하여 유연하게 처리하고 있습니다. 별도의 지역 코드(Region ID) 체계를 사용하지 않음으로써 "기타" 입력과 같은 개방형 지역 선택을 유연하게 수용할 수 있는 구조입니다. Agent는 이 정보를 바탕으로 사용자의 모호한 질문(예: "갈만한 곳 있어?")을 구체적인 로컬 검색 쿼리(예: "충장로 데이트 코스")로 변환하여 처리합니다.
