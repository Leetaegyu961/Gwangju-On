# Backend API & Architecture Details

이 문서는 Gwangju-On Backend(`FastAPI`)의 구조, API 명세, 그리고 AI Agent와의 연동 방식을 상세하게 설명합니다. Frontend와의 데이터 인터페이스(JSON Spec) 이해를 돕기 위한 예제도 포함되어 있습니다.

---

## 🏗 아키텍처 (Architecture)

Backend는 **FastAPI** 프레임워크를 기반으로 하며, AI Agent(`LangGraph`)를 호스팅하여 Frontend의 요청을 처리하는 역할을 합니다.

```mermaid
graph TD
    Client[Frontend (Next.js)] -->|REST API| API[FastAPI Server]
    API -->|Validation| Models[Pydantic Models]
    API -->|Session| UserDB[In-Memory User DB]
    API -->|Invoke| MainAgent[Main Agent (LangGraph)]
    API -->|Invoke| MiniAgent[Mini Agent (Optional)]
    MainAgent -->|Context| External[Google/Naver APIs]
```

### 주요 컴포넌트
1.  **FastAPI App (`main.py`)**: 서버 진입점, CORS 설정, 라우터 등록.
2.  **Routers (`api/`)**: 기능별 엔드포인트 분리.
    *   `chat.py`: AI 채팅 및 코스 생성 요청 처리. Main Agent를 실행합니다.
    *   `user.py`: 사용자 온보딩 및 설문 데이터 관리.
    *   `photo.py`: Google Photo API 이미지 프록시 (CORS 우회용).
3.  **Models (`models/`)**: Pydantic을 이용한 데이터 유효성 검사 및 스키마 정의.

---

## 📚 API 명세 (Endpoint Details)

Frontend가 실제 호출하는 주요 API 엔드포인트에 대한 설명입니다.

### 1. 사용자 온보딩 & 설문 (`/api/user`)

사용자의 세션을 생성하고 취향 정보를 업데이트합니다.

#### **POST** `/api/user/onboard`
*   **설명**: 새로운 사용자 세션 ID를 발급합니다.
*   **Request**:
    ```json
    {
      "nickname": "여행자1",
      "profileImage": "default.png"
    }
    ```
*   **Response**:
    ```json
    {
      "userId": "uuid-v4-string",
      "message": "User created"
    }
    ```

#### **POST** `/api/user/survey`
*   **설명**: 발급받은 `userId`에 설문 데이터를 매핑하여 저장합니다.
*   **Request**:
    ```json
    {
      "userId": "uuid-v4-string",
      "gender": "female",
      "age": "20s",
      "themes": ["healing", "cafe"],
      "companions": ["friends"],
      "budget": "medium"
    }
    ```
*   **Backend Logic**: `USER_DB[userId]`에 딕셔너리 형태로 저장되어, 이후 채팅 시 Context로 활용됩니다.

---

### 2. AI 채팅 (`/api/chat`)

핵심 기능인 여행지 코스 추천을 담당합니다.

#### **POST** `/api/chat`
*   **설명**: 사용자 메시지를 AI Agent에 전달하고 답변과 추천 코스를 반환합니다.
*   **Request**:
    ```json
    {
      "userId": "uuid-v4-string",
      "message": "동명동 분위기 좋은 카페랑 식당 추천해줘"
    }
    ```

*   **Internal Process (Backend 처리 과정)**:
    1.  `request.userId`로 `USER_DB`에서 설문 데이터 조회.
    2.  `src.agent.graph`의 `agent_app.ainvoke()` 실행 (메시지 + 설문 데이터 주입).
    3.  Agent가 내부적으로 Google/Naver 검색 및 Scoring v4 수행 후 병렬로 3가지 코스 생성.
    4.  Backend는 결과 JSON을 파싱하여 `allCourses` 및 `EvidenceCard` 리스트로 변환.

*   **Response (`ChatResponse`)**:
    ```json
    {
      "id": "msg-uuid",
      "role": "assistant",
      "text": "동명동의 핫한 장소들을 모아 3가지 코스로 준비했어요! 💖",
      "status": "done",
      "isDecisionPoint": true,
      "evidenceCards": [ ... ], // 첫 번째 코스의 장소들 (Legacy 호환용)
      "allCourses": [
        {
          "course_id": 1,
          "course_name": "맛집 탐방 코스",
          "course_description": "실패 없는 찐맛집 위주",
          "cards": [
            {
              "placeId": "p1",
              "name": "오디너리 디저트",
              "description": "케이크가 맛있는 카페",
              "img": "http://localhost:8000/api/photo?name=...",
              "score": 90,
              "reason": "티라미수 맛집"
            },
            ...
          ]
        },
        {
          "course_id": 2,
          "course_name": "힐링 산책 코스",
          ...
        },
        {
          "course_id": 3,
          "course_name": "인스타 핫플 코스",
          ...
        }
      ]
    }
    ```

---

### 3. 이미지 프록시 (`/api/photo`)

Google Places API의 이미지는 직접 호출 시 CORS 문제가 발생할 수 있어, Backend가 중계합니다.

#### **GET** `/api/photo?name={google_photo_resource_name}`
*   **설명**: Google Places API의 `places/{id}/photos/{id}` 리소스 이름을 받아 실제 이미지 바이너리를 스트리밍합니다.
*   **동작**:
    1.  Backend가 Google API `media` 엔드포인트 호출.
    2.  받은 이미지 데이터를 Frontend로 그대로 전달 (`Response(content=..., media_type="image/jpeg")`).
*   **URL 예시**: `http://localhost:8000/api/photo?name=places/ChIJ.../photos/AUc7...`

---

## 🛠 코드 구조 (Directory Structure)

```
backend/
├── api/             # API 엔드포인트 구현
│   ├── chat.py      # /api/chat (Agent 연동 핵심)
│   ├── user.py      # /api/user (In-Memory DB)
│   └── photo.py     # /api/photo (Image Proxy)
├── models/          # Pydantic 데이터 모델
│   ├── chat.py      # ChatRequest, ChatResponse, EvidenceCard, CourseInfo
│   └── user.py      # UserProfile, SurveyResult
└── run.py           # uvicorn 실행 스크립트
```

## ⚠️ 개발 시 유의사항

1.  **In-Memory DB**: 현재 사용자 데이터는 메모리(`USER_DB`)에 저장되므로, **서버 재실행 시 초기화**됩니다.
2.  **API Key**: `.env` 파일에 `GOOGLE_API_KEY` 등이 올바르게 설정되어야 Agent가 동작합니다.
3.  **Error Handling**: Agent 실행 중 오류 발생 시, 500 에러 대신 사용자에게 친절한 에러 메시지("죄송해요, 잠시 후 다시 시도해주세요")를 반환하도록 `try-except` 처리되어 있습니다.
