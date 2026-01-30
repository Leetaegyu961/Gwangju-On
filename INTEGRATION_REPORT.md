# 코드 통합 분석 보고서 및 이식 계획 (Code Integration Analysis & Blueprint)

## 1. 코드베이스 진단 (Codebase Diagnosis)
*   **사용자 코드 (Direction 2 - `backend/`):**
    *   **장점:** 고도화된 **응답 파싱 및 UI 로직** 보유. `EvidenceCards` 및 `recommended_courses` 구조를 통해 멀티 코스 프론트엔드를 지원함.
    *   **단점:** 메모리 기반 저장소(`USER_DB`) 사용, 구버전 TMap API 사용.
*   **팀원 코드 (Direction 3 - `backend_clone/`):**
    *   **장점:** **인프라 구축**. **MongoDB** 연동으로 데이터 영속성 확보, 정확도가 높은 `/search/around` TMap API 사용.
    *   **단점:** 프론트엔드가 요구하는 복잡한 응답 포맷 지원 부족.

## 2. 통합 청사진 (Integration Blueprint)
사용자의 고도화된 로직을 유지하면서, 팀원의 인프라 기능을 안전하게 이식함.

*   **A. 컨텍스트 검색 (Context Retrieval)**
    *   **기존:** 메모리(`USER_DB`)만 사용.
    *   **변경:** **하이브리드 전략** 적용. 1차로 메모리 확인, 없으면 MongoDB에서 조회하여 팀원의 로직대로 데이터를 평탄화(Flatten) 후 메모리에 캐싱. (`backend/api/chat.py` 수정됨)
*   **B. 세션 관리 (Session Management)**
    *   **변경:** 여행 계획 생성 완료 시, 세션 상태를 `"completed"`로 업데이트하는 로직 추가. (`backend/api/chat.py` 수정됨)
*   **C. TMap API 업그레이드**
    *   **변경:** 단순 POI 검색에서 반경 검색(`/tmap/pois/search/around`)으로 엔드포인트 변경. (`backend/api/tmap.py` 수정됨)

## 3. 실행 결과 (Execution Status)
*   **✅ 통합 완료.**
*   해커톤 환경의 신속한 진행을 위해, 위 분석된 내용을 바탕으로 **이미 코드를 수정하여 적용하였습니다.**
*   `backend/api/chat.py`: MongoDB 연동 및 세션 상태 업데이트 로직 이식 완료 (기존 응답 파싱 로직 보존).
*   `backend/api/tmap.py`: API 엔드포인트 교체 완료.

## 4. 추가 통합: 설문 및 인증 (Phase 2: Survey & Auth)
사용자 편의성 및 개인화를 위한 설문(Survey) 및 인증(Auth) 기능 통합 완료.

*   **Survey (Frontend):**
    *   팀원의 `SurveyScreen.tsx` 코드를 기반으로 UI를 대폭 개선 및 포팅.
    *   **기능 추가:** `region` (지역) 선택 기능 추가 및 코스 생성 트리거 연동.
    *   **Flow:** 설문 완료 시 `/chat?mode=course_init`으로 리다이렉트하여 자연스러운 대화 연결 구현.
*   **Auth (Full Stack):**
    *   **Google Login:** `LoginScreen.tsx` 및 `backend/api/auth.py`에 Google OAuth 2.0 연동 완료.
    *   **Login Button Fix:**
        *   **Issue:** 커스텀 로그인 버튼이 `google.accounts.id.prompt()` (One Tap UI)를 호출하여 반응이 없는 것처럼 보이는 문제.
        *   **Resolution:** 공식 `google.accounts.id.renderButton`으로 교체하여 안정적인 클릭 로그인을 보장하도록 수정.
        *   **Reliability:** `setTimeout` 재시도 로직을 추가하여 네트워크 지연 시에도 Google Script가 로드될 때까지 초기화를 재시도하도록 개선.
        *   **Dev UX:** `g_state` 쿠키 초기화 로직을 추가하여, 개발 중 One Tap 쿨다운(Exponential Cooldown)을 리셋하고 즉시 테스트 가능하도록 조치.
    *   **Data Migration:** 비로그인 상태(Guest)에서 생성한 데이터를 로그인 시 계정으로 이관하는 `migrate_user_data` 로직 구현 (`backend/api/auth.py`).
    *   `LoginScreen.tsx`에서 로그인 시 `guest_id`를 함께 전송하여 서버 측 마이그레이션 트리거.
*   **Chat Glue (Frontend):**
    *   `ChatScreen.tsx` 수정: `mode=course_init` 파라미터 감지 시, "가고 싶은 장소가 있나요?" 초기 질문을 자동 발송하여 설문 맥락을 이어나가도록 처리.
*   **Safety Check:**
    *   기존의 핵심 기능인 **"3-Course Generation & Display"** (AI가 3가지 코스를 생성하고 `EvidenceCards`로 보여주는 로직)는 수정 과정에서 **완벽하게 보존 및 검증됨.**

## 5. 버그 수정 (Bug Fixes)
*   **Google Login Button Fix:**
    *   **문제 (Issue):** 커스텀 버튼 클릭 핸들러가 `prompt()` (One Tap UI)를 사용하여 브라우저에 의해 억제될 경우 반응이 없는 것처럼 보이는 문제.
    *   **해결 (Fix):** 공식 `google.accounts.id.renderButton` 메서드로 교체하여 안정적인 로그인 흐름 보장.
*   **Agent Location Fix:**
    *   **문제 (Issue):** Agent의 `QueryPlannerNode`가 설문 조사(survey)의 `region` 데이터를 사용하지 않아 기본값인 "서울"로 설정되는 문제.
    *   **해결 (Fix):** `query_planner_node.py`를 업데이트하여 `region` 필드를 추출하고 이를 시스템 프롬프트(System Prompt)에 높은 우선순위로 주입하도록 수정.
*   **Auth Router 404 Fix:**
    *   **Issue:** The `/api/auth/google` endpoint returned `404 Not Found` because the `auth` router was defined but not included in the main FastAPI app.
    *   **Fix:** Updated `main.py` to correctly include `auth_router` with the prefix `/api`.
*   **Course Title Limit:**
    *   **Issue:** Generated course titles were too long (8+ chars) and truncated in the UI.
    *   **Fix:** Updated the prompt in `course_generation_node.py` to strictly enforce a maximum of 6 characters for course names.
*   **Image Loading Delay Fix:**
    *   **Issue:** Course images loaded slowly (2-3s delay) even after preloading.
    *   **Root Cause:** The `getCourseImage()` function returned a random URL each time. The URL preloaded into the cache was different from the URL subsequently requested by the Map component, causing a cache miss.
    *   **Fix:** Refactored `ChatScreen.tsx` to generate and persist the image URL once, ensuring consistency between the preloaded resource and the rendered component.
