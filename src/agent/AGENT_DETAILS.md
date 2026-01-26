# AI Agent 상세 구조 및 데이터 흐름

이 문서는 Gwangju-On 서비스의 핵심인 AI Agent의 내부 동작 과정을 상세하게 설명합니다. LangGraph를 기반으로 구성된 Agent가 **Frontend의 설문 데이터**를 어떻게 활용하며, **Backend**를 통해 어떤 데이터를 주고받는지 자세히 다룹니다.

---

## 🏗 전체 파이프라인 (LangGraph Workflow)

Agent는 다음과 같은 순차적 그래프 구조(`Graph`)로 동작합니다.

```mermaid
graph TD
    START --> QueryPlanner[Query Planner Node]
    QueryPlanner --> GooglePlace[Google Place Search Node]
    GooglePlace --> NaverBlog[Naver Blog Search Node]
    NaverBlog --> LLM[LLM Node (Answer Generation)]
    LLM --> END
```

---

## 🔗 Frontend ↔ Backend 데이터 연동 구조 (Integration)

사용자의 경험은 **설문조사(Survey)**에서 시작하여 **채팅(Chat)**으로 이어집니다. 이 과정에서 데이터가 어떻게 전달되고 활용되는지 확인해보겠습니다.

### 1단계: 사용자 프로필 및 취향 분석 (Survey)
**Frontend** (`SurveyScreen.tsx`) -> **Backend** (`api/user.py`)

사용자가 앱을 처음 실행하면 닉네임과 설문조사를 진행합니다. 이 데이터는 나중에 AI가 맞춤형 코스를 짤 때 핵심적인 단서가 됩니다.

1.  **Request (`POST /api/user/survey`)**:
    ```json
    {
      "userId": "user_12345",
      "gender": "female",
      "age": "20s",
      "themes": ["healing", "instagrammable"],
      "companions": ["couple"],
      "budget": "medium"
    }
    ```
2.  **Backend 저장**:
    *   `USER_DB` (In-Memory Dictionary)에 `userId`를 키(Key)로 하여 저장됩니다.
    *   예: `USER_DB["user_12345"] = { "gender": "female", ... }`

---

### 2단계: AI 채팅 요청 (Chat Request)
**Frontend** (`ChatScreen.tsx`) -> **Backend** (`api/chat.py`)

사용자가 구체적인 장소나 코스를 추천해달라고 채팅을 보냅니다.

1.  **Request (`POST /api/chat`)**:
    ```json
    {
      "userId": "user_12345",     // 이 ID로 서버에 저장된 취향을 찾습니다.
      "message": "동명동 분위기 좋은 카페 갔다가 저녁 먹을만한 식당 추천해줘"
    }
    ```
2.  **Backend 처리**:
    *   `USER_DB`에서 `user_12345`의 설문 데이터(`survey_data`)를 조회합니다. ("20대 여성, 힐링, 연인 동반...")
    *   Agent Graph를 실행할 때 `messages`와 `survey_data`를 함께 주입합니다.

---

## 🧩 3단계: AI Agent 내부 처리 상세 (Node Processing)

이제 LangGraph 내부에서 데이터가 어떻게 변환되는지 단계별로 살펴봅니다.

### ① Query Planner Node (검색 계획 수립)
사용자의 자연어 질문과 **설문 데이터(Context)**를 함께 고려하여 검색어를 생성합니다.

*   **Prompt Input (LLM에 들어가는 정보)**:
    > [사용자 정보]
    > - 20대 여성, 연인과 함께 여행, 힐링/감성 테마 선호
    >
    > [질문]
    > "동명동 분위기 좋은 카페 갔다가 저녁 먹을만한 식당 추천해줘"

*   **Output (JSON Plan)**:
    ```json
    {
      "place_queries": ["광주 동명동 인스타 감성 카페", "광주 동명동 분위기 좋은 데이트 맛집"],
      "result_count": 3,
      "reasoning": "20대 여성 사용자가 연인과 가기 좋은 '인스타 감성' 카페와 '분위기 좋은' 맛집을 각각 검색."
    }
    ```

### ② Google Place Search Node (장소 기본 정보 수집)
계획된 쿼리로 구글 지도 API를 검색합니다. 평점, 리뷰 수, 사진 ID, 좌표 등을 가져옵니다.

*   **입력**: `["광주 동명동 인스타 감성 카페", ...]`
*   **출력 (`place_data`)**:
    ```json
    [
      {
        "id": "Cafe_A",
        "name": "오디너리 디저트",
        "address": "광주 동구 동명동 123",
        "lat": 35.145, "lng": 126.920,
        "rating": 4.5,
        "photo_name": "places/PLACE_ID/photos/PHOTO_ID"
      },
      ...
    ]
    ```

### ③ Naver Blog Search Node (심층 리뷰 Enrichment)
장소 이름으로 네이버 블로그를 검색하고 RSS 내용을 긁어와 사용자 리뷰의 질을 높입니다.

*   **입력**: `place_data` 리스트
*   **출력 (`enriched_results`)**:
    ```json
    [
      {
        "place": { ...Google Data... },
        "blogs": [
          {
            "title": "동명동 데이트 코스 추천",
            "full_content": "남자친구랑 갔는데 분위기가 너무 좋았어요. 티라미수 강추!",
            ...
          }
        ]
      }
    ]
    ```

### ④ LLM Node (최종 JSON 생성)
모인 정보를 종합하여 Frontend가 바로 사용할 수 있는 포맷으로 응답을 생성합니다.

*   **System Prompt**: 
    > "Context에 있는 장소(ID: p1, p2...) 정보를 사용하여 20대 여성 커플을 위한 코스를 짜줘. 반드시 아래 JSON 포맷을 지켜."

*   **Final Output (JSON)**:
    ```json
    {
      "answer": "동명동의 **오디너리 디저트**에서 달콤한 시간을 보낸 후\n분위미 넘치는 **동명관**에서 저녁을 즐겨보세요! 💖",
      "courses": [
        {
          "id": "p1",
          "name": "오디너리 디저트",
          "type": "cafe",
          "lat": 35.145, "lng": 126.920,
          "reason": "티라미수가 맛있는 감성 카페"
        },
        {
          "id": "p4",
          "name": "동명관",
          "type": "restaurant",
          "lat": 35.146, "lng": 126.921,
          "reason": "엔틱한 분위기의 퓨전 맛집"
        }
      ]
    }
    ```

---

## 4단계: 결과 반환 및 시각화 (Response Parsing)
**Backend** (`api/chat.py`) -> **Frontend**

Backend는 Agent가 뱉어낸 JSON을 파싱하여 Frontend용 객체인 `EvidenceCard`로 변환합니다.

1.  **Backend Logic**:
    *   `courses` 배열을 순회하며 `EvidenceCard` 객체 생성.
    *   `lat`/`lng` 좌표가 포함되어 있어야 지도에 보여줄 수 있음.
    *   사진 URL은 Proxy URL(`http://localhost:8000/api/photo?name=...`)로 변환.

2.  **Response (`ChatResponse`)**:
    ```json
    {
      "id": "uuid-...",
      "role": "assistant",
      "text": "동명동의 오디너리 디저트에서...",
      "isDecisionPoint": true,
      "evidenceCards": [
        {
          "placeId": "p1",
          "name": "오디너리 디저트",
          "lat": 35.145, "lng": 126.920,
          "img": "http://localhost:8000/api/photo?name=...",
          ...
        },
        ...
      ]
    }
    ```

3.  **Frontend Action**:
    *   채팅창에 답변 표시.
    *   `isDecisionPoint: true`이므로 "코스 생성하기" 버튼 표시.
    *   버튼 클릭 시 `evidenceCards`의 좌표 데이터를 가지고 **지도 페이지(`MapView`)**로 이동.
