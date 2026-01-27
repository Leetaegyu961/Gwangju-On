# 🛠 Gwangju-On 최종 구현 사양서 (2026-01-27)

오늘 구현 및 개선된 광주ON 프로젝트의 기술 사양과 아키텍처 상세 내역입니다.

---

## 1. 시스템 환경 및 디버깅 결과
- **Frontend Config**: `next.config.mjs`에 `Cross-Origin-Opener-Policy: same-origin-allow-popups` 헤더를 설정하여 Google OAuth 팝업 통신 문제를 해결함.
- **Error Handling**: `app/onboarding/page.tsx`에 `Suspense` 경계를 적용하여 서버 사이드 렌더링 시의 비동기 오류(500 에러)를 차단함.

---

## 2. 사용자 및 권한 로직 (User Management)

### A. 판독기 (Member/Guest Detection)
- **로직**: `accessToken` 존재 여부와 `tempUserId`에 하이픈(`-`) 포함 여부로 판단.
  - **Guest ID**: 백엔드 `uuid.v4()` 생성 → `123e456...` (하이픈 포함)
  - **Member ID**: 구글 `sub` 값 → `1101694...` (숫자로만 구성)

### B. 데이터베이스 스키마 및 정책
- **컬렉션 분리**: 회원(`users`)과 게스트(`guests`)를 분리하여 저장.
- **TTL 인덱스**: `guests` 컬렉션의 `last_active_at` 필드에 30일(2,592,000초) 만료 인덱스 설정.
- **데이터 이관**: 로그인(`POST /api/auth/google`) 시 `guests` -> `users`로 프로필 및 여행 기록(`user_archive`) 이동 후 게스트 레코드 삭제.

---

## 3. 코스 아카이브 및 AI 시스템 (Course & RAG)

### A. 확장 데이터 모델 (`backend/models/course.py`)
- **PlaceMetadata**: `stay_duration`(기본 60분), `opening_hours`, `vibe_tags` 추가로 RAG 검색 품질 도모.
- **Course**: `summary_text`, `representative_image`, `share_id`를 추가하여 SNS 공유 및 아카이브 시각화 지원.

### B. AI 자동화 로직
- **Background Task**: 코스 저장(`POST /api/course/save`) 시 `generate_course_summary` 함수를 백그라운드 태스크로 실행.
- **Gemini 통합**: `gemini-1.5-flash` 모델을 사용하여 저장된 장소 리스트를 바탕으로 감성적인 제목과 요약문을 자동 생성.

---

## 4. 주요 API 엔드포인트

| Method | Endpoint | Description |
| --- | --- | --- |
| **POST** | `/api/auth/google` | 구글 로그인 및 게스트 데이터 마이그레이션 |
| **POST** | `/api/user/onboard` | 게스트 온보딩 정보 저장 (`guests` 컬렉션) |
| **PUT** | `/api/user/profile` | 회원 및 게스트의 프로필 정보 업데이트 |
| **POST** | `/api/course/save` | AI 추천 코스 영구 저장 및 AI 요약 생성 |
| **GET** | `/api/user/saved-courses` | 특정 사용자의 전체 아카이브 목록 조회 |

---

## 5. 프론트엔드 UI 컴포넌트
- **`SettingScreen.tsx`**: 로그인 상태에 따른 프로필 수정 및 로그인 유도 UI 분기 처리.
- **`ChatScreen.tsx`**: AI 답변 섹션에 '저장' 및 '지도로 이동' 버튼 통합, 3초 후 자동 리다이렉트 지연 로직 적용.
- **`MyPage.tsx`**: 동적 장소 태그 및 AI 생성 요약문 렌더링 지원.

---

이 문서는 오늘 완료된 모든 실제 코드 구현 사항을 기반으로 작성되었습니다.
