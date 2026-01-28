# AI Agent 상세 구조 및 데이터 흐름

이 문서는 Gwangju-On 서비스의 핵심인 AI Agent의 내부 동작 과정을 상세하게 설명합니다. LangGraph를 기반으로 구성된 Agent가 **Frontend의 설문 데이터**를 어떻게 활용하며, **Backend**를 통해 어떤 데이터를 주고받는지 자세히 다룹니다.

---

## 🏗 전체 파이프라인 (LangGraph Workflow)

Agent는 다음과 같은 순차적 그래프 구조(`Graph`)로 동작합니다. 최근 **Scoring Node**가 고도화되어 LLM 기반의 정성적 평가가 추가되었습니다.

```mermaid
graph TD
    START --> QueryPlanner[Query Planner Node]
    QueryPlanner --> GooglePlace[Google Place Search Node]
    GooglePlace --> NaverBlog[Naver Blog Search Node]
    NaverBlog --> Scoring[Scoring Node (Base + LLM Sentiment)]
    Scoring --> LLM[LLM Node (Course Generation)]
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
    *   `USER_DB`에서 `user_12345`의 설문 데이터(`survey_data`)를 조회합니다.
    *   Agent Graph를 실행할 때 `messages`와 `survey_data`를 함께 주입합니다.

---

## 🧩 3단계: AI Agent 내부 처리 상세 (Node Processing)

이제 LangGraph 내부에서 데이터가 어떻게 변환되는지 단계별로 살펴봅니다.

### ① Query Planner Node (검색 계획 수립)
사용자의 자연어 질문과 **설문 데이터(Context)**를 함께 고려하여 검색어를 생성합니다. `Structured Output` 기능을 사용하여 정해진 포맷의 계획을 수립합니다.

*   **Prompt Input (LLM에 들어가는 정보)**:
    *   사용자 정보 (성별, 나이, 여행 테마, 동행인)
    *   사용자 질문 (Last Message)

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
        "user_ratings_total": 120,
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
            "full_content": "남자친구랑 갔는데 분위기가 너무 좋았어요...",
            "bloggername": "맛집탐방러",
            "postdate": "20240101"
          }
        ]
      }
    ]
    ```

### ④ Scoring Node v4 (하이브리드 스코어링 시스템)
**정량적 평가(API 데이터)**와 **정성적 평가(LLM 감성 분석)**를 결합하여 가장 적합한 장소를 선정합니다.

*   **입력**: `enriched_results`
*   **1. 정량적 평가 (Base Score)**:
    *   **공공 데이터**: 모범 음식점(+1), 광주 맛집 리스트(+1)
    *   **Google 평점**: `(평점/5) * 2` (최대 2점)
    *   **Google 리뷰수**: `log10(리뷰수) * 0.5` (최대 2점)
*   **2. 정성적 평가 (LLM Sentiment Score - V4)**:
    *   LLM이 Google 리뷰(5개)와 Naver 블로그(3개) 요약을 읽고 4가지 차원을 평가합니다.
    *   **맛 (Taste)**: 0~2.0점
    *   **서비스/분위기 (Service)**: 0~2.0점
    *   **가성비 (Value)**: 0~1.0점
    *   **재방문 의사 (Revisit)**: 0~1.0점
*   **출력 (`scored_results`)**:
    ```json
    [
      {
        "place": { ... },
        "score": 8.5, // Total Score
        "score_breakdown": {
          "taste": 2.0,
          "service": 1.5,
          "value": 1.0,
          "revisit": 1.0,
          "reason": "맛과 분위기가 훌륭하며 재방문 의사가 높음"
        }
      }
    ]
    ```

### ⑤ LLM Node (코스 생성 및 최종 응답)
종합 점수가 높은 장소를 우선적으로 고려하여 **3가지 테마**의 코스를 제안합니다.

*   **System Prompt Context**:
    *   장소별 상세 정보 (ID: p1, p2...)
    *   종합 점수 및 감성 분석 요약
    *   Google & Naver Review Snippets

*   **Course Themes**:
    1.  **맛집 탐방 코스**: 점수 최상위 장소 중심
    2.  **효율 이동 코스**: 동선 최적화 중심
    3.  **인스타 핫플 코스**: 분위기/감성 점수 중심

*   **Final Output (JSON)**:
    ```json
    {
      "answer": "동명동의 핫한 장소들을 모아 3가지 코스로 준비했어요! 💖",
      "recommended_courses": [
        {
          "course_id": 1,
          "course_name": "맛집 탐방 코스",
          "course_description": "실패 없는 '찐맛집' 위주로 꽉 채운 코스",
          "places": [
            {
              "id": "p1", // Context의 ID 매핑
              "name": "오디너리 디저트",
              "type": "cafe",
              "lat": 35.145, "lng": 126.920,
              "reason": "티라미수 인생 맛집 (종합점수 1위)"
            },
            ...
          ],
          "total_budget": "약 5만원"
        },
        ... (코스 2, 3)
      ]
    }
    ```

---

## 4단계: 결과 반환 (Response Parsing)
**Backend** (`api/chat.py`) -> **Frontend**

Backend는 Agent가 뱉어낸 JSON을 파싱하여 Frontend로 전달합니다. `isDecisionPoint: true` 플래그를 통해 사용자가 지도로 이동하여 상세 코스를 확인할 수 있도록 유도합니다.
