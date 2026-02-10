# 광주-ON (Gwangju-ON) 프로젝트 전체 분석서

> AI 에이전트 기반 광주광역시 맞춤형 여행 코스 추천 서비스

---

## 1. 프로젝트 개요

### 1.1 서비스 설명
**광주-ON**은 AI 에이전트가 사용자의 취향, 설문 데이터, 과거 행동 이력을 분석하여 광주광역시의 맞춤형 여행 코스를 추천하는 풀스택 웹 애플리케이션입니다.

### 1.2 핵심 기능
- **AI 코스 추천**: LangGraph 기반 멀티노드 에이전트가 Parallel Hybrid RAG(Vector + Keyword)로 장소를 검색하고, LLM이 4차원 감성 채점 후 3가지 테마별 코스를 병렬 생성
- **개인화 시스템**: 사용자의 PICK/SKIP 행동, 테이스팅 노트, 설문 결과를 점진적으로 학습하여 Soft Boosting 적용
- **실시간 코스 수정 (Refine Agent)**: 전체 파이프라인 재실행 없이 Gemini 1회 호출 + 규칙 기반으로 2~3초 내 코스 부분 수정
- **타임라인/앨범**: 여행 완료 후 사진 업로드 및 폴라로이드 스타일 앨범 생성, 공유 기능
- **초대장 시스템**: 개인화된 초대장을 생성하여 재방문 유도

### 1.3 기술 스택
| 영역 | 기술 |
|------|------|
| **Frontend** | Next.js (App Router), TypeScript, Tailwind CSS, Framer Motion |
| **Backend** | FastAPI, Python 3.13, Motor (MongoDB async) |
| **AI/LLM** | Google Gemini (gemini-2.0-flash), LangChain, LangGraph |
| **Vector DB** | GCP Vertex AI Matching Engine (gemini-embedding-001) |
| **Database** | MongoDB (user sessions, preferences, logs) |
| **External APIs** | Google Places API (New), Tmap API, Naver Blog Search |
| **Infrastructure** | Docker, Google Cloud Run, GCS (사진 저장) |
| **인증** | Google OAuth 2.0, JWT (python-jose) |

---

## 2. 프로젝트 디렉토리 구조

```
google_team_project_YoungJunKim/
├── backend/                    # FastAPI 백엔드 서버
│   ├── main.py                 # FastAPI 앱 진입점 + CORS + 라우터 등록
│   ├── db.py                   # MongoDB 연결 관리 (Motor async)
│   ├── run.py                  # uvicorn 실행 스크립트
│   ├── api/                    # API 엔드포인트 모듈
│   │   ├── auth.py             # Google OAuth + JWT 인증
│   │   ├── chat.py             # AI 채팅 (SSE 스트리밍 + 일반)
│   │   ├── user.py             # 사용자 프로필, 설문, 통계
│   │   ├── journey.py          # 여행 세션 CRUD, 코스 저장/확정
│   │   ├── invitation.py       # 초대장 생성 (일반 + 개인화)
│   │   ├── tasting_note.py     # 테이스팅 노트 저장
│   │   ├── preference_utils.py # 선호도 점진 학습 유틸리티
│   │   ├── context_builder.py  # 개인화 컨텍스트 빌더 (LLM 요약)
│   │   ├── refine.py           # Refine Agent API 엔드포인트
│   │   ├── session.py          # 세션에 초대장 적용
│   │   ├── photo.py            # Google Places 사진 프록시 (캐시)
│   │   ├── place_info.py       # Mini Agent 연동 장소 정보 조회
│   │   ├── search.py           # Vertex AI Vector Search API
│   │   ├── tmap.py             # Tmap 경로/POI/역지오코딩
│   │   ├── maps.py             # Google Static Maps 이미지 생성
│   │   └── upload.py           # GCS 사진 업로드
│   ├── models/                 # Pydantic 데이터 모델
│   │   ├── user.py             # UserTripSession, SurveyData, UserPreferenceProfile 등
│   │   └── chat.py             # ChatRequest/Response, EvidenceCard, CourseInfo
│   └── service/
│       └── vector_search.py    # Vertex AI Vector Search 서비스 레이어
│
├── frontend/                   # Next.js 프론트엔드
│   ├── app/                    # Next.js App Router 페이지
│   │   ├── page.tsx            # 루트 → LoginScreen
│   │   ├── layout.tsx          # 전역 레이아웃 (Navigation, Google/Tmap SDK)
│   │   ├── globals.css         # 전역 CSS (Tailwind)
│   │   ├── login/page.tsx      # 로그인 페이지
│   │   ├── onboarding/page.tsx # 온보딩 (게스트)
│   │   ├── survey/page.tsx     # 설문조사
│   │   ├── chat/page.tsx       # AI 채팅
│   │   ├── map/page.tsx        # 지도 뷰 (메인 코스 표시)
│   │   ├── timeline/page.tsx   # 타임라인 앨범
│   │   ├── tasting-note/       # 테이스팅 노트
│   │   ├── history/page.tsx    # 코스 히스토리
│   │   ├── profile/page.tsx    # 마이페이지
│   │   ├── discovery/page.tsx  # 디스커버리
│   │   ├── wishlist/page.tsx   # 위시리스트
│   │   ├── travel/page.tsx     # 여행 뷰
│   │   └── invite/[courseId]/  # 초대장 동적 라우팅
│   ├── screens/                # 화면 컴포넌트
│   │   ├── LoginScreen.tsx     # Google 로그인 + 게스트 모드
│   │   ├── SurveyScreen.tsx    # 여행 취향 설문 (지역/테마/동행인/예산)
│   │   ├── ChatScreen.tsx      # AI 채팅 인터페이스
│   │   ├── MapView.tsx         # Tmap 지도 + 코스 표시 + SSE 로딩
│   │   ├── HistoryScreen.tsx   # 추천/확정 코스 히스토리
│   │   ├── TimelineScreen.tsx  # 앨범 목록 + 상세 뷰 + 공유
│   │   ├── TastingNoteScreen.tsx # 5단계 여행 평가
│   │   ├── HomeScreen.tsx      # 홈 화면
│   │   ├── MyPage.tsx          # 마이페이지
│   │   ├── ProfileSetupScreen.tsx # 프로필 설정
│   │   ├── WishlistScreen.tsx  # 위시리스트
│   │   └── TravelView.tsx      # 여행 뷰
│   ├── components/             # 재사용 컴포넌트
│   │   ├── Navigation.tsx      # 하단 네비게이션 바 (4탭)
│   │   ├── DiscoverySideModal.tsx
│   │   ├── auth/LoginModal.tsx
│   │   ├── user/GuestSettingsModal.tsx
│   │   ├── user/UserSettingsModal.tsx
│   │   └── invitation/InvitationModal.tsx
│   ├── features/               # 기능별 컴포넌트
│   │   ├── dashboard/AgentContextDashboard.tsx  # 에이전트 컨텍스트 대시보드
│   │   └── experience/
│   │       ├── InvitationPopup.tsx              # 초대장 팝업
│   │       ├── PlaceInteractiveCard.tsx         # 장소 카드
│   │       └── SummarySequence.tsx              # 요약 시퀀스
│   ├── services/
│   │   └── geminiService.ts    # API 클라이언트 (채팅, SSE, 코스 CRUD, Refine, Validate)
│   ├── utils/
│   │   ├── apiConfig.ts        # API URL 중앙 관리
│   │   └── courseImages.ts     # 카테고리별 이미지 매핑 유틸
│   └── types.ts                # TypeScript 타입 정의
│
├── src/                        # AI 에이전트 모듈
│   ├── agent/                  # 메인 코스 생성 에이전트 (LangGraph)
│   │   ├── graph.py            # 에이전트 그래프 정의 (8개 노드)
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── main.py             # CLI 실행 진입점
│   │   ├── config.py           # 설정 관리
│   │   ├── scoring_system.py   # 스코어링 시스템 (기본 + 개인화)
│   │   ├── nodes/              # 그래프 노드들
│   │   │   ├── query_planner_node.py     # 테마 3개 + 검색 쿼리 생성
│   │   │   ├── vector_search_node.py     # Vector DB 시맨틱 검색
│   │   │   ├── keyword_search_node.py    # Google Places 키워드 검색
│   │   │   ├── enrichment_node.py        # 후보 통합 + 상세정보 조회
│   │   │   ├── naver_blog_search.py      # 네이버 블로그 검색 (현재 바이패스)
│   │   │   ├── scoring_node.py           # LLM 4차원 감성 채점 + 코스 생성
│   │   │   ├── course_generation_node.py # LLM 코스 생성 (스코어링에서 이미 생성 시 스킵)
│   │   │   └── aggregator_node.py        # 결과 취합 + JSON 포맷팅
│   │   └── tools/
│   │       └── vector_db.py              # GCP Vertex AI Vector DB 클라이언트
│   │
│   ├── general_agent/          # 경량 장소 검색/추천 에이전트
│   │   ├── graph.py            # 4단계 순차 파이프라인
│   │   ├── state.py            # GeneralAgentState
│   │   └── nodes/
│   │       ├── query_analyzer.py    # 질문 분석
│   │       ├── search_node.py       # 통합 검색
│   │       ├── enrichment_node.py   # 상세 정보 조회
│   │       └── response_node.py     # LLM 응답 생성
│   │
│   ├── refine_agent/           # 코스 부분 수정 에이전트
│   │   ├── __init__.py         # 패키지 진입점
│   │   ├── intent_analyzer.py  # Gemini Structured Output 의도 분석
│   │   └── course_modifier.py  # 규칙 기반 코스 수정 (LLM 호출 없음)
│   │
│   └── mini_agent/             # 개별 장소 정보 조회 경량 에이전트
│       ├── mini_agent.py
│       ├── mini_agent_fc.py
│       ├── blog_search.py
│       ├── place_search.py
│       └── nodes/
│
├── data/                       # 정적 데이터
│   ├── Gwangju City Certified Exemplary Restaurant.json  # 모범 음식점
│   ├── gwangju_food_list.json                            # 광주 맛집 리스트
│   ├── tourism_data_full.json                            # 관광 데이터
│   └── invitation_courses.json                           # 초대장 코스 데이터
│
├── tests/                      # 테스트
├── static/                     # 정적 파일 (업로드 등)
├── docs/                       # 문서
│
├── pyproject.toml              # Python 의존성 (Poetry)
├── poetry.lock                 # 의존성 잠금 파일
├── Dockerfile                  # Cloud Run 배포용
├── .env.example                # 환경변수 템플릿
├── .gitignore
├── README.md
│
├── *.json                      # 지역별 음식점 데이터 (bukgu, namgu, seogu, gwangsan)
├── vectors*.json               # Vector DB 로컬 데이터
├── extracted_keywords_*.json   # 키워드 추출 결과
├── rss_collected_*.jsonl       # RSS 수집 데이터
├── place_summaries_*.json      # 장소 요약 데이터
│
├── pipeline_*.py               # 데이터 파이프라인 스크립트
├── generate_vectors.py         # 벡터 생성 스크립트
├── batch_generate_summaries.py # 배치 요약 생성
└── 기타 유틸리티 스크립트 (check_*.py, clean_*.py 등)
```

---

## 3. 백엔드 상세 분석

### 3.1 FastAPI 애플리케이션 (`backend/main.py`)

앱은 `Gwangju-On Backend`라는 제목으로 생성되며, lifespan 이벤트를 통해:
1. **시작 시**: MongoDB 연결 + 세션 만료 백그라운드 태스크 시작 (30분 미활동 세션 자동 만료)
2. **종료 시**: MongoDB 연결 종료

**등록된 라우터** (모두 `/api` prefix):
| 라우터 | 모듈 | 주요 기능 |
|--------|------|-----------|
| `chat` | `api/chat.py` | AI 채팅 (일반 + SSE 스트리밍) |
| `search` | `api/search.py` | Vertex AI Vector Search |
| `maps` | `api/maps.py` | Google Static Maps |
| `user` | `api/user.py` | 사용자 프로필/설문/통계 |
| `photo` | `api/photo.py` | Google Places 사진 프록시 |
| `place_info` | `api/place_info.py` | Mini Agent 장소 정보 |
| `tmap` | `api/tmap.py` | Tmap 경로/POI/역지오코딩 |
| `auth` | `api/auth.py` | Google OAuth + JWT |
| `journey` | `api/journey.py` | 여행 세션 CRUD |
| `tasting_note` | `api/tasting_note.py` | 테이스팅 노트 |
| `upload` | `api/upload.py` | GCS 사진 업로드 |
| `invitation` | `api/invitation.py` | 초대장 시스템 |
| `session` | `api/session.py` | 세션 관리 |
| `refine` | `api/refine.py` | Refine Agent |

### 3.2 데이터베이스 (`backend/db.py`)

MongoDB를 Motor(비동기 드라이버)로 연결합니다.
- 기본 URI: `mongodb://localhost:27017/`
- 기본 DB명: `gwangju_on`
- TTL 인덱스: `guests` 컬렉션에 30일 후 자동 삭제

**주요 컬렉션**:
| 컬렉션 | 용도 |
|--------|------|
| `users` | 사용자 계정 (Google 로그인) |
| `guests` | 게스트 계정 (TTL 30일) |
| `user_trip_sessions` | 여행 세션 (설문→채팅→코스 생성→완료) |
| `user_preferences` | 사용자 선호도 프로필 (테마 가중치) |
| `user_archive` | 여행 아카이브 |
| `user_activity_logs` | 사용자 행동 로그 |
| `detailed_interaction_logs` | 상세 인터랙션 로그 |
| `tasting_notes` | 테이스팅 노트 |
| `user_wishlist` | 위시리스트 |
| `refinement_sessions` | Refine Agent용 후보 풀 |
| `refinement_logs` | 수정 로그 |
| `personalized_invitations` | 개인화 초대장 |

### 3.3 인증 시스템 (`backend/api/auth.py`)

1. **Google OAuth 2.0**: 프론트엔드에서 Google ID Token을 받아 서버에서 검증
2. **JWT 발급**: 검증 성공 시 JWT 토큰 발급 (HS256, 기본 60분)
3. **데이터 마이그레이션**: 게스트→구글 로그인 시 세션/아카이브 데이터 이관
4. **토큰 검증**: `/auth/me` 엔드포인트로 현재 사용자 정보 조회

### 3.4 채팅 시스템 (`backend/api/chat.py`)

**핵심 흐름**:
1. 사용자 메시지 수신
2. **Intent Classification** (Gemini Structured Output):
   - `course`: "코스", "투어", "일정" 등의 키워드가 명시적으로 포함된 경우
   - `general`: 그 외 모든 요청 (장소 리스트, 단일 추천, 맛집 검색 등)
3. Intent에 따라 적절한 Agent 실행:
   - `course` → `src/agent/graph.py` (Course Agent)
   - `general` → `src/general_agent/graph.py` (General Agent)
4. 결과 파싱 (JSON → EvidenceCard/CourseInfo)
5. DB 저장 (채팅 히스토리 + 코스 자동 저장)
6. Refinement Pool 저장 (코스 수정용 후보 장소 풀)

**SSE 스트리밍** (`/chat/stream`):
- LangGraph `astream_events`를 사용하여 각 노드 진행 상황을 실시간 전송
- 프론트엔드에서 진행률 표시 (planning → searching → enriching → scoring → generating → done)

**입력 유효성 검증** (`/chat/validate`):
- Gemini로 여행/맛집 관련 유효한 요청인지 판별
- 무의미한 기호/낙서/관계없는 질문 필터링

### 3.5 개인화 시스템

#### 선호도 학습 (`backend/api/preference_utils.py`)
| 이벤트 | 학습 내용 | 증분 |
|--------|-----------|------|
| 설문 제출 | 선택 테마에 가중치 부여 | +1.0 per theme |
| 코스 확정 | 장소 카테고리/태그 학습 | +0.3 per tag |
| 테이스팅 노트 | 만족도→테마 조정 + 분위기/최애 장소 | +0.2/-0.1 |
| Discovery PICK | 카테고리 강화 | +0.15 |
| Discovery SKIP/REJECT | 카테고리 약화 | -0.05 |

- 가중치 범위: 0.0 ~ 5.0 (편향 방지)
- tanh 정규화가 스코어링 시점에서 적용 (5.0과 3.0의 실질 차이 최소화)

#### 컨텍스트 빌더 (`backend/api/context_builder.py`)
Agent 호출 전에 사용자의 개인화 데이터를 수집하고 LLM으로 3문장 요약문 생성:
1. 선호도 가중치 (상위 5개 테마)
2. 최근 테이스팅 노트 3건 (만족도, 분위기)
3. 최근 대화 히스토리 (마지막 4턴)

### 3.6 여행 세션 관리 (`backend/api/journey.py`)

**세션 상태 흐름**:
```
IN_PROGRESS → COMPLETED → COMPLETED_CANDIDATE
                ↓
             EXPIRED (30분 미활동)
```

**주요 API**:
| 엔드포인트 | 기능 |
|-----------|------|
| `POST /journey/save-final` | 코스 최종 저장 (확정/후보 구분) |
| `POST /journey/save-wishlist` | 위시리스트 저장 |
| `GET /journey/history/{userId}` | 여행 히스토리 조회 |
| `DELETE /journey/{sessionId}` | 여행 기록 삭제 |
| `PATCH /journey/{sessionId}/unselect` | 확정 해제 |
| `POST /journey/{course_id}/create-timeline` | 타임라인 생성 |
| `PATCH /journey/{sessionId}/update-photo` | 사진 URL 저장 |

### 3.7 Refine Agent API (`backend/api/refine.py`)

전체 파이프라인 재실행 없이 2~3초 내 코스 부분 수정:
1. Refinement Pool 로드 (이전 코스 생성 시 저장된 후보 장소 풀)
2. `src/refine_agent` 호출:
   - `analyze_refinement_intent()`: Gemini Structured Output으로 의도 분석
   - `apply_modification()`: 규칙 기반 코스 수정 (LLM 호출 없음)
3. DB 업데이트 + 수정 로그 저장

### 3.8 외부 API 연동

#### Google Places Photo Proxy (`backend/api/photo.py`)
- Google Places Photo Media를 서버 사이드에서 프록시하여 클라이언트에 전달
- TTLCache(1000개, 24시간)로 캐싱

#### Tmap API (`backend/api/tmap.py`)
- 자동차 경로 탐색 (`/tmap/routes`)
- 도보 경로 탐색 (`/tmap/routes/pedestrian`)
- 주변 POI 검색 (`/tmap/poi/around`)
- POI 검색 (`/tmap/poi/search`)
- 역지오코딩 (`/tmap/geo/reverse`)

#### Google Static Maps (`backend/api/maps.py`)
- 코스 경로를 포함한 정적 지도 이미지 생성
- 타임라인 앨범의 엔딩 슬라이드에서 사용

#### GCS 사진 업로드 (`backend/api/upload.py`)
- 사용자 사진을 Google Cloud Storage에 업로드
- 10MB 제한, 이미지 파일만 허용

---

## 4. 데이터 모델 상세

### 4.1 백엔드 모델 (`backend/models/user.py`)

```python
UserTripSession          # 여행 세션 (userId, status, intent_context, album_data)
  ├── IntentContext      # 의도 컨텍스트 (survey_data, chat_history, keywords)
  │   └── SurveyData    # 설문 데이터 (region, courses, themes, companions, budget)
  │       └── CoursePoint # 코스 포인트 (id, type, name, lat, lng, desc, tags)
  ├── Demographics       # 인구통계 (age, gender)
  └── UserActivityLog    # 활동 로그 (action_type: PICK/SKIP/REJECT)

UserPreferenceProfile    # 선호도 프로필
  ├── PreferenceWeights  # 가중치 (themes: Dict[str, float], price_sensitivity)
  └── BehaviorStats      # 행동 통계 (avg_spend, total_trips, most_visited_category)

UserAccount              # 사용자 계정 (id, email, name, picture, is_guest, is_onboarded)
UserArchive              # 아카이브 (id, userId, title, points, totalBudget)
TastingNoteEntry         # 테이스팅 노트 (satisfaction, atmosphere, movement, best_place)
DetailedInteractionLog   # 상세 인터랙션 (action, context_snapshot)
```

### 4.2 채팅 모델 (`backend/models/chat.py`)

```python
ChatRequest    # { message, userId }
ChatResponse   # { id, role, text, isDecisionPoint, evidenceCards, allCourses, status }
EvidenceCard   # { placeId, name, reason, reviewSummary, risks, trustScore, lat, lng, keywords, img }
CourseInfo      # { course_id, course_name, course_description, cards: List[EvidenceCard] }
ValidateRequest/Response  # 입력 유효성 검증
```

### 4.3 프론트엔드 타입 (`frontend/types.ts`)

```typescript
UserProfile     // { id, nickname, age, gender, isLoggedIn, preferences }
EvidenceCard    // { placeId, name, reason, reviewSummary, risks, trustScore, lat, lng, keywords, img }
CoursePoint     // { id, type, name, address, lat, lng, imageUrl, reason, evidence, desc, tags, transport, img }
SavedCourse     // { id, userId, title, points, totalBudget, createdAt, description, is_selected, timeline_generated, groupId }
CourseInfo       // { course_id, course_name, course_description, cards }
Message         // { id, role, text, isDecisionPoint, evidenceCards, allCourses, status, suggestions, showSurveyPrompt }
Place           // { id, name, category, description, imageUrl, tags, reviewSnippets, lat, lng }
```

---

## 5. AI 에이전트 시스템 상세 분석

### 5.1 Course Agent (`src/agent/`)

**LangGraph 그래프 구조** (8개 노드, 병렬 실행 포함):

```
START
  ↓
query_planner_node          # LLM: 테마 3개 + 검색 쿼리 생성
  ↓ (Fan-Out: Parallel)
├─ vector_retrieval_node    # Vector DB 시맨틱 검색 (쿼리당 k=20)
└─ keyword_retrieval_node   # Google Places Text Search (쿼리당 5~10개)
  ↓ (Fan-In: Merge)
enrichment_node             # 통합 + ID Resolution + Google Places Details 조회
  ↓ (Conditional)
[naver_blog_search_node]    # 조건부: 블로그 리뷰 검색 (현재 바이패스)
  ↓
scoring_node                # LLM 4차원 감성 채점 + Slot-based 코스 생성
  ↓ (Fan-Out: Parallel)
├── generate_course_1       # 테마 1 코스 (스코어링에서 이미 생성 시 스킵)
├── generate_course_2       # 테마 2 코스
└── generate_course_3       # 테마 3 코스
  ↓ (Fan-In: Aggregate)
aggregator_node             # 결과 취합 + JSON 포맷팅
  ↓
END
```

#### AgentState
```python
class AgentState(TypedDict):
    messages: Sequence[BaseMessage]       # 대화 히스토리 (add_messages reducer)
    current_step: str                     # 현재 단계
    query_plan: dict | None               # LLM 생성 검색 계획
    vector_candidates: list | None         # Vector DB 검색 결과
    keyword_candidates: list | None        # Keyword 검색 결과
    enriched_results: list | None          # 통합 상세 데이터
    scored_results: list | None            # 스코어링된 결과
    final_answer: str | None               # 최종 응답 (JSON 문자열)
    survey_data: dict | None               # 사용자 설문 데이터
    themes: list[str] | None              # QueryPlanner 생성 3가지 테마
    generated_courses: Annotated[list, operator.add]  # 병렬 코스 결과 (Reducer)
    userId: str | None                     # 사용자 ID (개인화용)
    run_blog_search: bool | None           # 블로그 검색 실행 여부
    personalization_context: str | None    # 개인화 컨텍스트 요약
```

#### Query Planner Node
- **입력**: 사용자 메시지 + 설문 데이터 + 개인화 컨텍스트
- **출력**: `QueryPlan { themes: [str, str, str], place_queries: [str], result_count: int, reasoning: str }`
- **규칙**: 테마는 2~4글자 명사만 (지역명/수식어 금지), 쿼리는 최대 3개

#### Vector Retrieval Node
- GCP Vertex AI Matching Engine에서 시맨틱 검색
- `gemini-embedding-001` 모델로 쿼리 임베딩 생성
- 쿼리당 k=20, 병렬 실행 후 중복 제거
- 클라이언트 사이드 필터링 (지역 + 콘텐츠 존재 여부)

#### Keyword Retrieval Node
- Google Places API (New) `places:searchText` 엔드포인트 사용
- 최소한의 필드만 요청 (name, displayName, formattedAddress, location, priceLevel, types)
- 비동기 병렬 검색 (aiohttp)

#### Enrichment Node
- Vector + Keyword 후보를 통합하고 중복 제거
- ID Resolution + Details Fetching을 단일 병렬 작업으로 최적화
- Google Places Details API로 평점, 리뷰, 사진, 가격 등 조회
- Gemini로 외국어 식당명 → 한글 변환

#### Scoring Node (v4, Batch Processing)
**4차원 LLM 감성 채점**:
| 차원 | 범위 | 기준 |
|------|------|------|
| 맛 (taste) | 0~2점 | 극찬/호평/보통/비호평/혹평 |
| 서비스/분위기 (service) | 0~2점 | 친절/깔끔/분위기 |
| 가성비 (value) | 0~1점 | 저렴/적당/비쌈 |
| 재방문 의사 (revisit) | 0~1점 | 또 갈 것/안 갈 것 |

- 배치 크기: 5개 (LLM 호출 횟수 감소)
- 비동기 병렬 실행

**Slot-based 코스 생성 (v6)**:
1. 설문에서 설정한 코스 구성(타입 시퀀스)을 "슬롯"으로 사용
2. 각 슬롯의 타입에 맞는 장소를 선택
3. Weighted Sampling + Exploration Weight (0.4) 적용
4. Backtracking 감지 페널티 (왔다갔다 방지)
5. 테마별 키워드 보너스 적용

#### Scoring System (`src/agent/scoring_system.py`)

**기본 스코어링** (RestaurantScoringSystem):
| 항목 | 점수 | 비고 |
|------|------|------|
| 모범 음식점 | +1점 | 광주시 인증 |
| 광주 맛집 | +1점 | 공공데이터 |
| Google 평점 | 최대 2점 | (rating/5.0) * 2 |
| Google 리뷰 수 | 최대 2점 | log10 스케일 |

**개인화 스코어링** (PersonalizedScoringSystem):
- 기본 스코어 + 개인화 가산점 (tanh Soft Boosting, MAX_BOOST=2.0)
- 세션 테마 실시간 반영 (+2.0 per match)
- 가격 민감도 보정 (민감: 비싼곳 -0.5, 둔감: 고급 +0.2)
- 중복 매칭 방지 (matched_prefs set)

#### Course Generation Node
- Scoring Node에서 이미 코스를 생성한 경우 스킵 (효율화)
- 3개 노드가 병렬로 실행, 각각 하나의 테마 코스 생성
- LLM에게 scored_results + 테마 정보 전달하여 코스 생성

#### Aggregator Node
- 병렬 생성된 코스들을 course_id 순으로 정렬
- 최종 JSON 응답 포맷팅: `{ answer, recommended_courses }`

### 5.2 General Agent (`src/general_agent/`)

코스가 아닌 일반 장소 검색/추천용 경량 파이프라인 (4단계 순차):

```
START → query_analyzer → search_node → enrichment_node → response_node → END
```

- **서베이 데이터/개인화 스코어링 없음**
- Intent Classification에서 `general`로 분류된 요청 처리
- 예: "동명동 카페 리스트", "점심 뭐 먹지?", "떡갈비 맛집"

### 5.3 Refine Agent (`src/refine_agent/`)

코스 생성 후 부분 수정 전문 에이전트 (2~3초 응답):

#### Intent Analyzer (`intent_analyzer.py`)
Gemini Structured Output으로 사용자 수정 의도 분석:

```python
class RefinementIntent(BaseModel):
    action: str      # swap/remove/add/shift_location/change_theme/change_type
    course_idx: int  # 대상 코스 인덱스
    slot_idx: int    # 대상 장소 인덱스
    criteria: str    # 조건 키워드
    direction: str   # 위치 방향 (north/south/east/west)
    new_type: str    # 변경할 타입 (식당/카페/숙박/놀거리)
    reasoning: str   # 분석 이유
```

#### Course Modifier (`course_modifier.py`)
LLM 호출 없이 규칙 기반으로 즉시 실행:

| 액션 | 동작 |
|------|------|
| `swap` | 지정 슬롯의 장소를 후보 풀에서 조건에 맞는 다른 장소로 교체 |
| `remove` | 지정 슬롯의 장소 제거 |
| `add` | 후보 풀에서 조건/타입에 맞는 장소를 코스에 추가 |
| `shift_location` | 지정 방향의 장소로 교체 |
| `change_type` | 장소 타입 변경 (예: 식당→카페) |
| `change_theme` | 전체 코스를 새 분위기에 맞춰 재구성 |

- `find_replacement()`: 후보 풀에서 키워드 매칭 + 코스 중심점 거리 보너스/페널티 + Weighted Sampling
- `find_by_direction()`: 현재 장소 기준 특정 방향의 가장 가까운 장소 3개 중 랜덤 선택

### 5.4 Vector DB 클라이언트 (`src/agent/tools/vector_db.py`)

**GCPVectorDB 싱글톤**:
1. 로컬 메타데이터 로드: `extracted_keywords_*.json` (동명동/시내권/조대권)
2. Vertex AI Matching Engine 연결 (asia-northeast3)
3. `gemini-embedding-001`로 쿼리 임베딩 생성
4. 검색 시 2000개를 가져와서 클라이언트 사이드 필터링:
   - 지역 필터 (파일명 기반 매핑)
   - 콘텐츠 존재 여부 (키워드가 있는 장소만)

---

## 6. 프론트엔드 상세 분석

### 6.1 앱 구조 (Next.js App Router)

**라우팅**:
| 경로 | 화면 | 설명 |
|------|------|------|
| `/` | LoginScreen | 로그인/게스트 진입 |
| `/login` | LoginScreen | Google 로그인 페이지 |
| `/onboarding` | ProfileSetupScreen | 게스트 온보딩 |
| `/survey` | SurveyScreen | 여행 취향 설문 |
| `/chat` | ChatScreen | AI 채팅 |
| `/map` | MapView | Tmap 지도 + 코스 표시 |
| `/timeline` | TimelineScreen | 타임라인 앨범 |
| `/tasting-note` | TastingNoteScreen | 테이스팅 노트 |
| `/history` | HistoryScreen | 코스 히스토리 |
| `/profile` | MyPage | 마이페이지 |
| `/discovery` | DiscoveryScreen | 장소 디스커버리 |
| `/wishlist` | WishlistScreen | 위시리스트 |
| `/travel` | TravelView | 여행 뷰 |
| `/invite/[courseId]` | 동적 라우팅 | 초대장 상세 |

**하단 네비게이션** (Navigation.tsx):
- AI 가이드 (survey/chat)
- 지도 (map)
- 타임라인 (timeline)
- 마이페이지 (profile)
- 로그인/온보딩/여행뷰에서는 숨김

### 6.2 사용자 흐름 (User Flow)

```
[로그인 화면]
  ├── Google 로그인 → [설문] 또는 [지도] (온보딩 여부에 따라)
  └── 게스트 모드 → [온보딩] → [설문]

[설문 화면] (SurveyScreen)
  ├── 지역 선택 (동명동/양림동/충장로 등 + GPS + 기타)
  ├── 코스 구성 (식당/카페/놀거리/숙박, 최대 8개)
  ├── 테마 (데이트/힐링/액티비티/맛집탐방)
  ├── 동행인 (혼자/친구/연인/가족)
  ├── 예산 (5만~50만원 듀얼 슬라이더)
  └── [코스 생성 확인하기] → [채팅] → [지도]

[채팅 화면] (ChatScreen)
  ├── AI 채팅 (입력 유효성 검증 → Agent 실행)
  ├── 자동 코스 생성 시 → [지도]로 자동 이동
  └── 설문 기반 코스 생성 버튼

[지도 화면] (MapView)
  ├── Tmap 지도에 코스 마커/라인 표시
  ├── SSE 스트리밍 진행률 표시 (Agent 실행 중)
  ├── 코스 전환 (3개 코스 스와이프)
  ├── 장소 카드 상세 정보 (Mini Agent)
  ├── 코스 수정 (Refine Agent)
  └── [여행 완료] → [테이스팅 노트]

[테이스팅 노트] (TastingNoteScreen)
  ├── 5단계 평가:
  │   1. 만족도 (별점 1~5)
  │   2. 분위기 (감성/활기/전통)
  │   3. 이동 동선 (효율적/보통/힘들었어요)
  │   4. 최애 장소 (코스 내 장소 선택)
  │   5. AI 큐레이션 품질 (완벽/보통/개선 필요)
  └── [완성] → [타임라인]

[타임라인] (TimelineScreen)
  ├── 앨범 목록 (폴라로이드 스타일 카드)
  ├── 앨범 상세 (커버 + 장소별 사진/코멘트 + 루트 지도)
  ├── 추억 앨범 생성 (캐러셀 뷰)
  ├── 사진 업로드 (GCS)
  └── 공유 (네이티브 공유 / 이미지 다운로드)

[히스토리] (HistoryScreen)
  ├── 추천 코스 히스토리 (전체)
  └── 확정 코스 목록 (is_selected=true)
```

### 6.3 GeminiService (`frontend/services/geminiService.ts`)

프론트엔드 API 클라이언트 중앙 모듈:

| 메서드 | 기능 |
|--------|------|
| `processRequest()` | 일반 채팅 요청 |
| `processRequestStream()` | SSE 스트리밍 채팅 (진행률 콜백) |
| `validateInput()` | 입력 유효성 검증 |
| `refineCourse()` | 코스 수정 (Refine Agent) |
| `getUserProfile()` | 토큰/ID 기반 프로필 조회 |
| `saveCourse()` | 코스 저장 (localStorage + 서버) |
| `getCourses()` | 코스 목록 조회 |
| `getUserStatistics()` | 사용자 통계 |
| `getAgentContext()` | 에이전트 컨텍스트 (대시보드용) |
| `getPersonalizedInvitation()` | 개인화 초대장 조회 |
| `markPersonalizedInvitationViewed()` | 초대장 열람 처리 |
| `syncUser()` | 사용자 정보 동기화 |

### 6.4 주요 화면 상세

#### LoginScreen
- Google One Tap 로그인 + Google Sign-In 버튼 렌더링
- 게스트 모드 ("계정 없이 이용하기")
- 로그인 성공 시 `access_token` + `user_profile` + `temp_user_id` localStorage 저장
- 온보딩 완료 여부에 따라 `/survey` 또는 `/map`으로 리다이렉트

#### SurveyScreen
- 지역, 코스 구성, 테마, 동행인, 예산 설정
- 초대장 팝업 (1/3 확률, 개인화 초대장 우선)
- 설문 제출 시 `/user/survey` API 호출 → 세션 생성
- "코스 생성 확인하기" → `/chat?mode=course_init`

#### ChatScreen
- 입력 유효성 검증 후 채팅 전송
- 코스 생성 요청 시 `/map?auto_generate=true` 로 이동 (MapView에서 SSE 실행)
- 코스 결과(isDecisionPoint) 도착 시 자동 지도 이동
- 이미지 프리로딩 (코스 장소 이미지 캐시)

#### TimelineScreen
- **리스트 뷰**: 폴라로이드 스타일 앨범 카드 (중첩 사진 콜라주)
- **상세 뷰**:
  - 커버 섹션 (타이틀 + 콜라주)
  - 타임라인 (장소별 코멘트 + 사진 업로드)
  - 추억 앨범 모달 (캐러셀: 커버 → 장소별 → 엔딩)
  - 엔딩 슬라이드: 사진 그리드 + Static Map
- html2canvas로 이미지 캡처/다운로드
- Web Share API로 네이티브 공유

#### TastingNoteScreen
- 5단계 설문 (Framer Motion 애니메이션)
- 완료 시 테이스팅 노트 API 저장 + localStorage 정리 → 타임라인 이동

---

## 7. 인프라 및 배포

### 7.1 Docker
```dockerfile
FROM python:3.13-slim
# Poetry로 의존성 설치 → backend/, src/, data/, vectors.json 복사
# Cloud Run PORT=8080
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### 7.2 환경변수 (`.env.example`)
| 카테고리 | 변수 |
|---------|------|
| Google AI Studio | `GOOGLE_API_KEY` |
| GCP | `GOOGLE_CLOUD_API_KEY`, `GOOGLE_CLOUD_PROJECT` |
| Naver | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` |
| Tmap | `TMAP_APP_KEY` |
| Google OAuth | `GOOGLE_CLIENT_ID` |
| JWT | `JWT_SECRET`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| MongoDB | `MONGO_URI`, `DATABASE_NAME` |
| Self-Reference | `API_URL` |
| Frontend CORS | `FRONTEND_URL` |
| GCS | `GCS_BUCKET_NAME`, `GCS_KEY_PATH` |
| Vertex AI | `VERTEX_INDEX_ENDPOINT_ID`, `VERTEX_DEPLOYED_INDEX_ID` |
| LLM | `GEMINI_MODEL` |

### 7.3 Python 의존성 (`pyproject.toml`)
- Python >= 3.13
- 주요: langchain, langchain-google-genai, langgraph, fastapi, motor, google-cloud-aiplatform
- 빌드: Poetry

---

## 8. 데이터 파이프라인

프로젝트 루트에 다수의 파이프라인 스크립트가 존재합니다:

| 스크립트 | 용도 |
|---------|------|
| `pipeline_all.py` / `pipeline_all_vm.py` | 전체 데이터 파이프라인 (RSS 수집→키워드 추출→요약→벡터 생성) |
| `pipeline_namgu.py` | 남구 특화 파이프라인 |
| `collect_rss_*.py` | RSS 데이터 수집 (네이버 블로그) |
| `extract_keywords_pro.py` | LLM 키워드 추출 |
| `batch_generate_summaries.py` | 배치 장소 요약 생성 |
| `generate_vectors.py` | 임베딩 벡터 생성 |
| `clean_json_*.py` | 데이터 정제 |
| `ingest_local_data.py` | 로컬 데이터 적재 |
| `convert_to_vertex_search.py` | Vertex Search 형식 변환 |

**데이터 파일**:
- `extracted_keywords_*.json`: 지역별 키워드 추출 결과
- `place_summaries_*.json`: 장소별 LLM 요약
- `rss_collected_*.jsonl`: RSS 수집 원본 데이터
- `vectors*.json`: 임베딩 벡터 데이터
- `bukgu.json`, `namgu.json`, `seogu.json`, `gwangsan.json`: 구별 음식점 데이터

---

## 9. 핵심 아키텍처 패턴

### 9.1 Parallel Hybrid RAG
- **Vector Search** (시맨틱): 의미적으로 유사한 장소 발견 (gemini-embedding-001)
- **Keyword Search** (키워드): Google Places API로 정확한 매칭
- 두 결과를 Fan-In으로 병합 후 중복 제거 및 상세 정보 조회

### 9.2 LangGraph Fan-Out/Fan-In
- **Retrieval Phase**: query_planner → [vector, keyword] → enrichment
- **Generation Phase**: scoring → [course1, course2, course3] → aggregator
- `generated_courses: Annotated[list, operator.add]` Reducer로 병렬 결과 자동 합치기

### 9.3 Soft Boosting (개인화)
```
raw_score = sum(matched_weights) + sum(session_theme_boosts)
soft_score = tanh(raw_score) * MAX_BOOST(2.0)
final = base_quality_score + soft_score + price_adjustment
```
- tanh 함수로 점수가 무한정 커지지 않도록 정규화
- 같은 태그의 중복 매칭 방지 (matched_prefs set)

### 9.4 SSE (Server-Sent Events) 스트리밍
- LangGraph `astream_events(version="v2")`로 각 노드 시작/종료 이벤트 수신
- 노드별 진행률/메시지 매핑하여 클라이언트에 실시간 전송
- 프론트엔드에서 진행 바 + 아이콘 + 메시지 표시

### 9.5 Intent-based Agent Routing
```
사용자 메시지 → classify_intent(Gemini) → course / general
                                            ↓          ↓
                                    Course Agent   General Agent
                                    (8노드 파이프라인)  (4노드 파이프라인)
```

### 9.6 Refinement 아키텍처
```
사용자 수정 요청 → analyze_refinement_intent (Gemini 1회)
                         ↓
                  RefinementIntent (structured output)
                         ↓
                  apply_modification (규칙 기반, LLM 없음)
                         ↓
                  수정된 코스 반환 (2~3초)
```
- 기존 Agent 파이프라인(28초) 대비 ~10배 속도 개선

---

## 10. MongoDB 스키마 참고

### user_trip_sessions
```json
{
  "sessionId": "uuid",
  "group_id": "uuid (같은 세션에서 생성된 코스 그룹)",
  "userId": "google_sub_id",
  "status": "IN_PROGRESS|COMPLETED|COMPLETED_CANDIDATE|EXPIRED",
  "is_selected": false,
  "title": "코스 이름",
  "course_description": "코스 설명",
  "intent_context": {
    "survey_data": { "region": "동명동", "courses": [...], "themes": [...], "companions": [...], "budget": [10, 30] },
    "chat_history": [{ "role": "user|assistant", "content": "...", "timestamp": "..." }]
  },
  "album_data": [{ "id": "p1", "name": "장소명", "lat": 35.0, "lng": 126.0, "desc": "설명", "img": "url" }],
  "total_courses": 4,
  "ai_summary": "AI 추천 요약",
  "timeline_generated": false,
  "memory_spots": [...],
  "tasting_notes": {...},
  "created_at": "ISO",
  "completed_at": "ISO",
  "last_activity_at": "ISO"
}
```

### user_preferences
```json
{
  "userId": "google_sub_id",
  "last_updated": "ISO",
  "preference_weights": {
    "themes": { "데이트": 2.3, "맛집": 1.5, "카페": 0.8 },
    "price_sensitivity": 0.5
  }
}
```

### refinement_sessions
```json
{
  "userId": "google_sub_id",
  "refinement_pool": [
    { "id": "places/...", "name": "장소명", "address": "...", "lat": 35.0, "lng": 126.0,
      "rating": 4.5, "total_reviews": 120, "photo_name": "places/.../photos/...",
      "keywords": {...}, "score": 7.5, "type": "식당" }
  ],
  "current_courses": [...],
  "created_at": "ISO"
}
```

---

## 11. 요약

광주-ON은 LangGraph 기반 멀티에이전트 시스템과 Parallel Hybrid RAG를 핵심으로 하는 AI 여행 코스 추천 서비스입니다. Course Agent(8노드), General Agent(4노드), Refine Agent(의도 분석+규칙 기반)의 3가지 에이전트가 사용자 의도에 따라 자동 라우팅되며, Soft Boosting 개인화와 SSE 실시간 스트리밍으로 사용자 경험을 강화합니다. 프론트엔드는 Next.js + Tmap SDK로 지도 기반 코스 시각화를, 백엔드는 FastAPI + MongoDB로 세션/선호도/이력 관리를 담당합니다.
