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
- **AI Agent**: LangChain & LangGraph
- **LLM**: Google Gemini (via `langchain-google-genai`)
- **Package Manager**: Poetry

### **AI Agent Pipeline**
1. **Query Planner**: 사용자 요청을 분석하여 검색 키워드 생성
2. **Google Place Search**: Google Maps API를 통해 장소 정보 및 평점 검색
3. **Naver Blog Search**: Naver Search API를 활용하여 최신 블로그 리뷰 및 현지 반응 분석
4. **Answer Generation**: 수집된 정보를 바탕으로 Gemini가 최종 답변 및 코스(JSON) 생성

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
├── src/                     # AI Agent 로직 (LangGraph)
│   └── agent/
│       ├── graph.py         # 에이전트 실행 그래프 정의
│       ├── nodes/           # 각 단계별 노드 (LLM, 검색 등)
│       └── tools/           # 외부 API 연동 도구
├── main.py                  # Backend 메인 애플리케이션 진입점
├── run_backend.py           # Backend 실행 스크립트
├── pyproject.toml           # Python 프로젝트 설정 (Poetry)
└── integration_plan.md      # 통합 계획 문서
```

---

## ✨ 주요 기능 (Key Features)

1. **AI 맞춤형 코스 설계**: 
   - 사용자의 취향을 설문(`Survey`)으로 분석.
   - "동명동 분위기 좋은 카페 추천해줘"와 같은 자연어 질의 처리.
   - LangGraph 기반의 검색 에이전트가 최신 정보를 반영하여 코스 제안.

2. **인터랙티브 지도 (Interactive Map)**:
   - AI가 제안한 장소를 TMAP 위에 마커와 경로로 시각화.
   - `EvidenceCard`를 통해 각 장소의 상세 정보 및 추천 이유 제공.

3. **실시간 정보**:
   - Google Places의 평점 정보와 Naver Blog의 최신 리뷰를 결합하여 신뢰도 높은 정보 제공.

---

Developed by **YoungJun Kim & Gwangju-On Team**
