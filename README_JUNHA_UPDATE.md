# 🛠️ Gwangju-On 프로젝트 상세 수정 로그 (2026-02-03)

## 📂 파일 변경 요약 (File Change Summary)

### ✨ 신규 생성 (Created)
- **`backend/api/maps.py`**: Google Static Maps API와 통신하기 위한 백엔드 프록시 로직 구현 파일.

### 📝 수정됨 (Modified)
- **`frontend/screens/TimelineScreen.tsx`**: 
  - 지도 렌더링 방식 전면 교체 (Tmap SDK → Static Map Image).
  - 공유하기 기능(Web Share/Clipboard) 추가.
  - 엔딩 슬라이드 및 앨범 리스트 UI 디자인 개선.
- **`frontend/screens/MapView.tsx`**: 
  - 정적 경로 보기 기능을 **실시간 도보 내비게이션(내 위치 추적)**으로 기능 업그레이드.
- **`frontend/screens/MyPage.tsx`**: 
  - 전체 테마 컬러 변경 (오렌지 → **블루**).
  - 마스코트 이미지 배경 장식 추가 및 프로필 UI 수정.
- **`frontend/screens/LoginScreen.tsx`**: 
  - 전체 테마 컬러 변경 (오렌지 → **블루**) 및 배경 장식 톤 조정.
- **`main.py`**: 
  - 신규 생성된 `maps` 라우터를 FastAPI 앱에 등록.

---

## 1. 🗺️ 타임라인 지도 캡처 시스템 전면 개편 (Timeline Map Upgrade)

### 🚨 문제 발생 (Problem)
- **증상**: `TimelineScreen`에서 생성된 카드 이미지를 `html2canvas`로 캡처할 때, 지도 영역이 빈 화면(흰색/투명)으로 저장되는 현상 발생.
- **원인 분석**:
  - 기존에는 Tmap Javascript V2 SDK를 사용하여 클라이언트 사이드(브라우저 Canvas/WebGL)에서 지도를 렌더링했습니다.
  - `html2canvas` 라이브러리는 외부 도메인(Tmap 서버)에서 로드된 이미지나 WebGL 컨텍스트(Tained Canvas)에 대해 보안 정책(CORS)상 접근을 차단하거나 렌더링을 건너뛰는 한계가 있습니다.

### 💡 해결 솔루션 (Solution): Google Static Maps 도입
브라우저 렌더링을 포기하고, **백엔드에서 이미 생성된 지도 이미지 파일(PNG)을 받아와서 표시**하는 방식으로 아키텍처를 변경했습니다.

### 💻 상세 수정 내역 (Code Changes)

#### A. Backend: `backend/api/maps.py` (New File)
- **Static Map Proxy 구현**:
  - `POST /api/maps/static` 엔드포인트를 신설했습니다.
  - 프론트엔드로부터 `center`({lat, lng}), `zoom`, `markers`(Array), `path`(Array) 데이터를 수신합니다.
  - Google Static Maps API URL을 생성하고, 서버 측에서 `requests`를 통해 이미지를 받아옵니다.
  - 받아온 이미지를 그대로 `Response(content=..., media_type="image/png")`로 반환하여, 프론트엔드가 바이너리 데이터를 직접 쓸 수 있게 했습니다.

#### B. Frontend: `frontend/screens/TimelineScreen.tsx` (Major Update)
- **Tmap 제거 및 이미지 대체**: 
  - `initTmap` 등 클라이언트 SDK 로직을 제거하고, `useEffect`에서 `/api/maps/static`을 호출하여 지도 이미지를 Blob으로 받아옵니다.
  - `<div id="map">` 대신 `<img src={mapImageUrl} />` 태그를 사용하여 캡처 호환성을 완벽하게 확보했습니다.

---

## 2. 📤 공유하기 기능 추가 (Share Functionality)

### 구현 목적
사용자가 생성된 여행 코스 카드를 다운로드만 하는 것이 아니라, 모바일 메신저(카카오톡 등)나 SNS로 즉시 공유할 수 있도록 기능을 확장했습니다.

### 💻 상세 수정 내역 (`TimelineScreen.tsx`)

#### A. `handleShare` 함수 구현
- **이미지 캡처**: 다운로드와 동일하게 `html2canvas`로 해당 DOM(`cardRef`)을 고해상도(`scale: 2`) 이미지 blob으로 변환합니다.
- **Platform-Specific Logic**:
  1.  **모바일 (Navigator.share)**: `navigator.canShare` 지원 시, 네이티브 공유 시트를 호출하여 카카오톡, 메시지 등으로 파일을 바로 전송합니다.
  2.  **PC (Clipboard API)**: `navigator.clipboard.write`를 사용하여 이미지를 클립보드에 복사합니다. (채팅방 붙여넣기 가능)

#### B. UI 추가
- 다운로드 버튼 좌측에 **Share2 아이콘 버튼**을 추가하여 접근성을 높였습니다.

---

## 3. 🚶‍♂️ 실시간 도보 내비게이션 (Real-time Navigation) - MapView Update

### 개요
기존 `MapView.tsx`의 단순 경로 보기 기능을 **"내 위치 기반 실시간 길안내"** 기능으로 업그레이드했습니다. 이제 사용자는 본인의 현재 위치에서 다음 목적지까지의 경로를 실시간으로 확인하며 이동할 수 있습니다.

### 💻 상세 수정 내역 (`frontend/screens/MapView.tsx`)

#### A. 내비게이션 로직 (`startNavigation`, `stopNavigation`)
- **Geolocation API 활용**: `navigator.geolocation.getCurrentPosition`으로 초기 위치를 잡고, `watchPosition`으로 실시간 이동 경로를 추적합니다.
- **Tmap API 연동**:
  - EndPoint: `https://apis.openapi.sk.com/tmap/routes/pedestrian` (보행자 경로)
  - Start: 내 실시간 위치 (User Location)
  - End: 현재 선택된 목적지 (Target Spot)
  - 매번 경로를 다시 계산하지 않고 코스 이동 시 최적 경로를 보여줍니다.

#### B. UI 및 시각화 (Visuals)
- **내 위치 마커 (Pulse Effect)**:
  - 파란색 점과 퍼져나가는(Ping) 애니메이션 효과(`<span class="animate-ping">`)를 CSS로 구현하여 현재 위치를 직관적으로 표시했습니다.
- **버튼 액션**:
  - 버튼 클릭 시 "도보 안내" ↔ "안내 종료"로 상태가 토글됩니다.
  - 내비게이션 중에는 남은 예상 소요 시간이 실시간으로 표시됩니다.

---

## 4. 🎨 UI/UX 디테일 개선 (Timeline Improvements)

### A. 엔딩 슬라이드 (Ending Slide)
- **Wide Grid**: 사진 배열을 가로로 긴 2분할(`aspect-[2.5/1]`)로 변경하여 지도 영역을 넓게 확보했습니다.
- **디자인 폴리싱**: 사진 오버레이 그라데이션을 부드럽게(`from-black/70`) 조정하고, 텍스트 정렬을 최적화했습니다.

### B. 앨범 리스트 (Dynamic Covers)
- 코스 장소 개수(1, 2, 3+)에 따라 앨범 표지 디자인이 폴라로이드(1장), 겹친 사진(2장), 콜라주(3장)로 동적으로 변하도록 개선했습니다.

---

## 5. 🔵 디자인 테마 변경: Blue Theme (MyPage & Login)

### 개요
프로젝트의 메인 컬러 톤을 **오렌지(#FF6B00)**에서 신뢰감과 시원함을 주는 **파란색(#3B82F6, Tailwind Blue-500)** 계열로 전면 교체했습니다.

### 💻 상세 수정 내역

#### A. `frontend/screens/MyPage.tsx`
- **테마 변경**: 배경색(`bg-[#F5F8FF]`) 및 모든 포인트 컬러를 블루 톤으로 수정.
- **마스코트 통합**: 기존의 단순 아이콘 대신 `mascot_full.png`를 배경 장식으로 활용하여 브랜드 아이덴티티를 강화했습니다.

#### B. `frontend/screens/LoginScreen.tsx`
- **테마 변경**: 로그인 화면의 그라데이션, 그림자, 텍스트 색상을 모두 파란색 계열로 통일했습니다.
- **애니메이션**: 마스코트 비디오 주변의 Glow 효과를 블루/인디고 컬러로 매칭했습니다.

---

## 6. 🧹 코드 관리 및 리팩토링
- **Dependencies**: React 19와 `framer-motion` 호환 이슈 해결을 위해 `MotionDiv` 래퍼 도입.
- **Cleanup**: Tmap V2 관련 Legacy 코드(Script 로딩 등) 및 미사용 상태 변수 정리.

---
*Last Updated: 2026-02-03 11:47*
*Modified by: AI Assistant (Antigravity)*