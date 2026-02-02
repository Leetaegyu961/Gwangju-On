# Gwangju-On (광주온) - AI 여행 코스 플래너

광주광역시를 방문하는 여행객을 위한 **AI 기반 맞춤형 여행 코스 추천 서비스**입니다.  
사용자의 성향(나이, 동반자, 여행 스타일 등)을 분석하여 Google Gemini AI가 최적의 여행 경로를 설계하고, TMAP을 통해 시각화하여 제공합니다.

---

## 🏗 아키텍처 (Architecture)

### **Frontend**
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Visualization**: TMAP API (지도/경로 표시)

### **Backend**
- **Framework**: FastAPI
- **Main Agent**: LangGraph (Stateful, Complex Workflow)
- **Mini Agent**: Node-based Lightweight Agent (Quick Search)
- **LLM**: Google Gemini (via `langchain-google-genai`)
- **Package Manager**: Poetry

### **AI Agent Pipeline (Main Agent)**
1. **Query Planner**: 사용자 요청 및 설문 데이터를 분석하여 3가지 테마 및 검색 키워드 생성
2. **Google Place Search**: Google Maps API를 통해 장소 정보 및 평점 검색
3. **Naver Blog Search**: Naver Search API & RSS를 활용하여 상세 리뷰 본문 수집
4. **Scoring Node v4**: 
   - **정량적 평가**: 공공 데이터(모범음식점 등) 및 Google 평점
   - **정성적 평가**: LLM을 활용한 감성 분석 (맛/서비스/가성비/재방문 의사)
5. **Parallel Course Generation**: 3가지 테마별 코스를 병렬로 동시 생성
6. **Aggregator**: 결과 취합 및 최종 답변 생성

---

## 🚀 시작하기 (Getting Started)

### 사전 요구사항 (Prerequisites)
- **Python**: 3.13 이상 3.15 미만
- **Node.js**: 최신 LTS 버전
- **Poetry**: Python 의존성 관리 도구

### 1. Backend 설정 (Server)

```bash
# Backend 디렉토리 의존성 설치
poetry install

# 서버 실행 (Root 디렉토리에서)
python run_backend.py
# 또는
uvicorn main:app --reload
```
*서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.*

### 2. Frontend 설정 (Client)

```bash
cd frontend

# 의존성 설치
npm install
# 또는
yarn install

# 개발 서버 실행
npm run dev
```
*웹 애플리케이션은 `http://localhost:5000`에서 실행됩니다.*

### 3. 환경 변수 설정 (Environment Variables)

프로젝트 루트 및 `frontend` 폴더에 각각 환경 변수 파일이 필요합니다.

**Root (`.env`)**
```env
# Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key

# Google Places / Maps API Key
GOOGLE_PLACES_API_KEY=your_places_api_key
GOOGLE_MAPS_API_KEY=your_maps_api_key
GOOGLE_CLOUD_API_KEY=your_cloud_api_key # Mini Agent용

# Naver Search API Key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
```

**Frontend (`frontend/.env.local`)**
```env
# TMAP API Key
NEXT_PUBLIC_TMAP_APP_KEY=your_tmap_app_key
```

---

## 📂 프로젝트 구조 (Project Structure)

```
.
├── backend/                 # FastAPI 백엔드 코드
│   ├── api/                 # API 엔드포인트 (Chat, User, Photo)
│   └── models/              # Pydantic 데이터 모델
├── frontend/                # Next.js 프론트엔드 코드
│   ├── app/                 # Next.js 페이지 (App Router)
│   ├── components/          # React 컴포넌트
│   └── screens/             # 주요 기능별 스크린 (Chat, Map, Survey 등)
├── src/                     # AI Agent 로직
│   ├── agent/               # Main Agent (LangGraph)
│   │   ├── graph.py         # 에이전트 실행 그래프 (Parallel Pipeline)
│   │   ├── nodes/           # 각 단계별 노드 (QueryPlanner, Scoring v4 등)
│   │   └── state.py         # Agent State 정의
│   └── mini_agent/          # Mini Agent (Lightweight)
│       ├── mini_agent.py    # Mini Agent Orchestrator
│       └── nodes/           # Independent Nodes
├── main.py                  # Backend 메인 애플리케이션 진입점
├── run_backend.py           # Backend 실행 스크립트
├── pyproject.toml           # Python 프로젝트 설정 (Poetry)
└── mini_agent_structure.md  # Mini Agent 상세 구조 문서
```

---

## ✨ 주요 기능 (Key Features)

1. **AI 맞춤형 코스 설계**: 
   - 사용자의 취향을 설문(`Survey`)으로 분석.
   - 3가지 테마(예: 맛집, 힐링, 가성비)를 자동 추출하여 다양한 옵션 제공.
   - **Scoring v4**: LLM이 리뷰를 직접 읽고 정성적 평가를 수행하여 "진짜 맛집" 추천.

2. **인터랙티브 지도 (Interactive Map)**:
   - AI가 제안한 장소를 TMAP 위에 마커와 경로로 시각화.
   - `EvidenceCard`를 통해 각 장소의 상세 정보 및 추천 이유 제공.

3. **고성능 데이터 처리**:
   - **Parallel Execution**: 코스 생성 단계를 병렬화하여 응답 시간 단축.
   - **Mini Agent**: 간단한 장소 검색을 위한 경량화 에이전트 별도 탑재.
   - **Image Proxy**: Google Photos API의 CORS 문제를 해결하는 프록시 서버 내장.

---

Developed by **YoungJun Kim & Gwangju-On Team**
