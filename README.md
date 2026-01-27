# Gwangju-On Google Login & MongoDB Integration Guide

이 디렉토리는 광주ON 프로젝트에 구현된 **구글 OAuth(FedCM) 로그인** 및 **MongoDB 비동기 연동** 기능을 다른 프로젝트로 쉽게 이식하기 위해 핵심 파일들을 모아둔 곳입니다.

## 📁 주요 구성 파일

### 1. Backend (FastAPI + Motor)
- `backend/db.py`: MongoDB 비동기 연결 및 **게스트 TTL 인덱스(30일)** 설정 포함.
- `backend/api/auth.py`: 구글 ID 토큰 검증, JWT 발행, **익명 데이터 병합(Migration)** 로직 포함.
- `backend/api/course.py`: **AI 코스 아카이브 저장 및 Gemini 요약 생성** API.
- `backend/models/course.py`: 확장된 장소 메타데이터(체류시간, 태그 등) 및 코스 모델.
- `.env`: 필요한 환경 변수 예시 (JWT_SECRET, GOOGLE_CLIENT_ID 등).

### 2. Frontend (Next.js + Tailwind)
- `frontend/screens/LoginScreen.tsx`: 구글 GSI SDK(FedCM) 연동 화면. 표준 로그인 버튼 및 One-Tap 로직 포함.
- `frontend/app/layout.tsx`: Tmap 및 Google SDK 스크립트 로드 구조.
- `frontend/.env.local`: 프론트엔드용 Google Client ID 및 API URL 설정.

## 🚀 통합 방법 (Integration Steps)

### Step 1: 백엔드 적용
1. `backend/` 하위 파일들을 대상 프로젝트의 동일한 경로에 복사합니다.
2. `main.py` (또는 앱 진입점)에서 다음과 같이 라우터를 추가하고 DB를 연결합니다:
   ```python
   from backend.api import auth
   from backend.db import db

   # Lifespan 추가 (DB 연결용)
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       await db.connect_to_storage()
       yield
       await db.close_storage()

   app = FastAPI(lifespan=lifespan)
   app.include_router(auth.router, prefix="/api")
   ```

### Step 2: 프론트엔드 적용
1. `LoginScreen.tsx`를 복사하고 원하는 경로에 배치합니다.
2. `layout.tsx`의 스크립트 로드 부분(`Tmap SDK` 등)을 확인하여 반영합니다.
3. 구글 클라우드 콘솔에서 **승인된 자격 증명 원본**에 `http://localhost:5000`(또는 사용 중인 포트)을 추가합니다.

### Step 3: 데이터 마이그레이션 확인
- 이 로직은 사용자가 비로그인 상태에서 서비스를 이용(게스트ID 생성)하다가 로그인했을 때, 기존 데이터를 자동으로 새 계정으로 이전해 줍니다.
- 이 기능을 위해 `localstorage`의 `temp_user_id`를 활용합니다.
- **2026-01-27 업데이트**: 게스트 정보는 30일 후 자동 삭제되며, 로그인 시 `users` 컬렉션으로 모든 아카이브가 안전하게 이전됩니다.

### 3. AI & Storytelling (New for V2)
- `backend/api/story.py`: **AI 여행 스토리(일기) 생성** 및 테마 컬러 제안 API.
- `frontend/screens/MyPage.tsx`: 저장된 코스, 장소, 일기를 탭으로 관리하는 대시보드.
- `frontend/components/DiscoverySideModal.tsx`: AI 기반 실시간 장소 요약 카드.

## 🚀 통합 방법 (Integration Steps)

### Step 1: 백엔드 적용
1. `backend/` 하위 파일 및 `api/story.py`를 대상 프로젝트에 복사합니다.
2. `main.py`에서 `story.router`를 포함시키고 MongoDB 연결 설정을 확인합니다.

### Step 2: 프론트엔드 적용
1. `LoginScreen.tsx` 및 `MyPage.tsx`, `DiscoverySideModal.tsx`를 반영합니다.
2. `GeminiService.ts`를 업데이트하여 AI API 및 오프라인 폴백 로직을 활성화합니다.

### Step 3: 안정성 확보 (V2 업데이트)
- **Tmap 최적화**: 경로 렌더링 시 직선 구간이 발생하지 않도록 `LineString` 병합 로직을 사용합니다.
- **오프라인 데모 보장**: 서버 끊김 시 `mockScenario.ts`를 통해 고품질 모의 데이터를 제공합니다.
- **보안 설정**: `COOP` 정책 및 CORS 설정을 `main.py`와 `next.config.mjs`에서 확인하세요.

## ⚠️ 주의사항
- **포트 설정**: 현재 프론트엔드 포트 5000번에 최적화되어 있습니다. 포트 변경 시 백엔드 CORS 설정을 반드시 업데이트하세요.
- **FedCM**: 최신 브라우저 정책에 따라 `use_fedcm_for_prompt: true` 옵션이 적용되어 있습니다.
