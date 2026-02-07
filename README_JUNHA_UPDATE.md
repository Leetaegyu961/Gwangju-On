# 🛠️ Gwangju-On Project Development Log (2026-02-03 ~ 02-07)

이 문서는 **2026년 2월 3일부터 7일**까지 진행된 **타임라인 UI 전면 리뉴얼, DB 연동, 공유 기능 고도화, 초대장 기능 통합, 게스트 권한 관리** 등 모든 개발 사항을 빠짐없이 기록한 통합 로그입니다.
나중에 코드를 병합하거나 수정 내역을 추적할 때 이 문서를 참고하십시오.

---

## 📅 Day 1: UI/UX 리뉴얼 & 기본 기능 구현 (2026-02-03)

### 1. 👤 마이페이지 UI 개선 (`frontend/screens/MyPage.tsx`)
사용자의 프로필 정보(나이, 성별)를 시각적으로 보여주는 배지(Badge) 기능을 추가했습니다.

*   **프로필 배지 추가**: 이름 하단에 `[20대]` `[여성]` 형태의 태그 표시.
*   **실시간 반영**: 설정 팝업 데이터 변경 시 즉시 UI 업데이트.

```typescript
{/* User Profile Badges */}
<div className="flex gap-2 justify-center mb-3">
    {profile?.age && <span className="text-blue-600 bg-blue-50 ...">{profile.age}</span>}
    {profile?.gender && <span className="text-indigo-500 bg-indigo-50 ...">{profile.gender}</span>}
</div>
```

### 2. 🎨 Timeline UI 전면 리뉴얼 (`frontend/screens/TimelineScreen.tsx`)
앱의 아이덴티티 강화를 위해 **Blue Theme & Mascot Identity**를 적용했습니다.

*   **Blue Theme**: 배경색을 밝은 블루(`bg-[#F5F8FF]`)로 변경, 카드 그림자 및 테두리를 블루 톤으로 통일.
*   **Mascot Animation**: 상단 헤더 및 로딩 화면에 마스코트 캐릭터 배치.
*   **Grid Layout**: 사진 개수(2장, 4장)에 따라 최적화된 격자 레이아웃 적용.

### 3. ✍️ 사용자 코멘트 편집 기능 (`Editable Description`)
AI가 생성한 장소 설명을 사용자가 직접 수정할 수 있도록 기능을 추가했습니다.
*   **Textarea 도입**: 리스트 뷰의 텍스트 영역을 클릭하여 바로 수정 가능.
*   **Fallback Logic**: 사용자가 내용을 비우면 기존 AI 설명(`spot.desc`)이 자동으로 다시 표시됨.

---

## 📅 Day 2: 기능 고도화 및 Merge 가이드 (2026-02-04)

### 4. 🔙 Backend API 추가 (`backend/api/journey.py`)
여행 기록 관리를 위한 핵심 API 2종을 구현했습니다.

**A. 여행 히스토리 조회 (`get_journey_history`)**
```python
@router.get("/journey/history/{userId}")
async def get_journey_history(userId: str):
    db = await get_database()
    # COMPLETED 상태인 여행만, 최신순 정렬
    return list(db["user_trip_sessions"].find({"userId": userId, "status": "COMPLETED"}).sort("completed_at", -1))
```

**B. 여행 삭제 (`delete_journey`)**
```python
@router.delete("/journey/{sessionId}")
async def delete_journey(sessionId: str):
    # DB에서 해당 세션(여행) 영구 삭제
    await db["user_trip_sessions"].delete_one({"sessionId": sessionId})
```

---

### 5. 🖥️ Frontend 기능 로직 구현 (`frontend/screens/TimelineScreen.tsx`)
디자인된 UI에 실제 데이터를 연결하고 고급 기능을 구현했습니다. 병합 시 아래 코드를 그대로 사용하십시오.

#### A. DB 데이터 우선 조회 (`fetchHistory`)
로컬 스토리지 대신 DB를 먼저 조회하고, 실패 시 로컬을 확인하는 안정적인 로직으로 변경했습니다.
```typescript
const fetchHistory = async () => {
    const userId = localStorage.getItem('temp_user_id');
    // 1. API Fetch
    const res = await fetch(`${API_URL}/api/journey/history/${userId}`);
    if (res.ok) {
        // ... DB 데이터 매핑 (albums 상태 업데이트) ...
    } else {
        loadFromLocalStorage(); // Fallback
    }
};
```

#### B. 앨범 삭제 기능 (`handleDeleteAlbum`)
앨범 카드 우상단의 **삭제(휴지통) 버튼** 기능입니다.
*   `confirm` 창으로 사용자 의사 확인.
*   UI에서 즉시 제거(Optimistic Update) 후 백엔드 요청 전송.

#### C. **[핵심]** 공유 기능 완전체 (`shareAllSlidesAsFiles`)
단일/전체 공유, 그리고 **브라우저 보안 이슈(NotAllowedError) 해결** 로직이 포함된 최종 코드입니다.

```typescript
// 전체 슬라이드 캡처 및 공유 (실패 시 다운로드 전환)
const shareAllSlidesAsFiles = async () => {
    // ... (초기화 및 캡처 루프: html2canvas 사용) ...

    try {
        if (files.length > 0) {
            // [PC/Mobile 공통] 공유 가능 여부 확인
            if (navigator.canShare && navigator.canShare({ files })) {
                try {
                    await navigator.share({ files, title: '광주 여행 앨범' });
                } catch (shareError: any) {
                    // [Error Handling] 보안 정책으로 차단 시 -> 다운로드
                    if (shareError.name === 'NotAllowedError' || shareError.message.includes('user gesture')) {
                        alert("보안 정책으로 자동 공유가 차단되었습니다. 대신 이미지를 다운로드합니다. 💾");
                        performDownload(files);
                    }
                }
            } else {
                // [PC] 미지원 환경 -> 다운로드
                alert("이 기기에서는 동시 공유를 지원하지 않습니다. 다운로드합니다.");
                performDownload(files);
            }
        }
    } catch (e) {
        alert("오류 발생");
    }
};
```

---

### 6. 🗺️ 지도 UX 개선 (`frontend/screens/MapView.tsx`)

#### A. 코스 확정 시 확인 절차 (`handleConfirmCourse`)
*   **Issue**: 저장 버튼 클릭 시 묻지도 않고 화면이 이동되어 당황스러움.
*   **Fix**: `confirm`을 사용하여 "이동하시겠습니까?" 묻도록 수정.

```typescript
if (confirm(`총 ${finalSpots.length}개의 장소로 코스가 확정되었습니다!\n타임라인으로 바로 이동하시겠습니까?`)) {
    router.push('/timeline');
} else {
    setToastMessage("저장되었습니다. (지도 화면 유지)");
}
```

#### B. 로그 관련 (참고사항)
*   지도 진입 시 터미널에 뜨는 `[Planner]` 로그는, 사용자를 위한 **'추가 추천 코스(Invitation)'**를 백그라운드에서 준비하는 과정이므로 정상 동작입니다.

---

## 📅 Day 3: 초대장 기능 통합 & 게스트 권한 관리 (2026-02-07)

### 7. 🎁 초대장 기능 통합 및 이미지 연동

#### A. 초대장 코스 이미지 추가 (`data/invitation_courses.json`)
초대장에 표시되는 7개 코스(C1~C7)의 각 장소에 실제 이미지를 연결했습니다.

**변경 사항**:
*   `data/course_image/` 폴더의 28개 이미지 파일을 `frontend/public/course_image/`로 복사
*   `invitation_courses.json`의 모든 장소에 `img` 필드 추가
*   경로 형식: `/course_image/c1-1.png`, `/course_image/C1-2.jpg` 등

```json
{
    "id": "c1-1",
    "name": "오웬기념각",
    "type": "역사",
    "lat": 35.140,
    "lng": 126.915,
    "desc": "1914년에 세워진 광주에서 가장 오래된 서양식 건물 중 하나입니다.",
    "img": "/course_image/c1-1.png"
}
```

#### B. InvitationPopup 이미지 매핑 (`frontend/features/experience/InvitationPopup.tsx`)
초대장 팝업에서 `img` 필드를 `imageUrl`로 매핑하여 실제 이미지를 표시하도록 수정했습니다.

```typescript
places: course.places.map((p: any, idx: number) => ({
    ...p,
    // invitation_courses.json의 img 필드를 imageUrl로 매핑
    imageUrl: p.img || p.imageUrl || getCourseImage([p.type || "여행"], p.name)
}))
```

---

### 8. 🔐 게스트 권한 관리 시스템 구축

게스트 사용자와 로그인 사용자를 명확히 구분하여, 게스트는 체험만 가능하고 데이터는 저장되지 않도록 시스템을 구축했습니다.

#### A. 초대장 수락 시 게스트 처리 (`frontend/features/experience/InvitationPopup.tsx`)

**문제점**:
*   게스트가 초대장을 수락하면 백엔드에 저장되어 "확정한 코스"에 표시됨
*   게스트가 초대장 수락 시 로그인 화면으로 리다이렉트됨

**해결 방법**:
```typescript
// 1. 게스트 체크 추가
const hasAccessToken = typeof window !== 'undefined' ? !!localStorage.getItem('access_token') : false;

// 2. 로그인 사용자만 백엔드에 저장
if (userId && hasAccessToken) {
    // 백엔드 저장 로직
    await fetch(`${API_URL}/api/journey/save-final`, { ... });
} else if (userId && !hasAccessToken) {
    // 게스트는 백엔드에 저장하지 않음
    console.log("ℹ️ Guest user - invitation not saved to backend");
}

// 3. 게스트도 지도로 이동 가능
if (hasAccessToken || hasTempUserId) {
    router.push('/map'); // 게스트도 바로 지도로 이동
}
```

#### B. 타임라인 게스트 접근 차단 (`frontend/screens/TimelineScreen.tsx`)

**문제점**: 게스트가 타임라인을 볼 수 있음

**해결 방법**:
```typescript
const fetchHistory = async () => {
    const userId = typeof window !== 'undefined' ? localStorage.getItem('temp_user_id') : null;
    const hasAccessToken = typeof window !== 'undefined' ? !!localStorage.getItem('access_token') : false;
    
    // 게스트는 타임라인을 표시하지 않음
    if (!userId || !hasAccessToken) {
        setAlbums([]);
        return;
    }
    // ... 로그인 사용자만 백엔드에서 데이터 조회
};
```

#### C. 히스토리/확정 코스 게스트 접근 차단 (`frontend/services/geminiService.ts`)

**문제점**: 게스트가 "확정한 코스"를 볼 수 있음

**해결 방법**:
```typescript
async getCourses(): Promise<SavedCourse[]> {
    const userId = localStorage.getItem('temp_user_id');
    const hasAccessToken = !!localStorage.getItem('access_token');
    
    // 게스트는 백엔드에서 가져오지 않음
    if (!userId || !hasAccessToken) {
      return [];
    }
    // ... 로그인 사용자만 백엔드 조회
}
```

#### D. 코스 확정 버튼 게스트 차단 (`frontend/screens/MapView.tsx`)

**기존 로직 확인**:
*   `checkIsGuest()` 함수 존재 (Line 110)
*   `handleConfirmCourse()` 함수에서 게스트 체크 수행 (Line 1041-1045)
*   게스트가 "이 코스로 결정하기" 버튼 클릭 시 로그인 모달 표시

```typescript
const handleConfirmCourse = async () => {
    // [Guest Check]
    if (checkIsGuest()) {
        setModalFeature("코스 확정 및 저장");
        setShowLoginModal(true);
        return;
    }
    // ... 로그인 사용자만 코스 확정 로직 실행
};
```

---

### 9. 🧹 UI 정리 및 버그 수정

#### A. MapView 하트 아이콘 제거 (`frontend/screens/MapView.tsx`)
*   사용하지 않는 "찜하기" 버튼(하트 아이콘) 완전 제거
*   `Heart` import 제거
*   Line 1790-1803의 찜하기 버튼 코드 삭제

#### B. MapView 네비게이션 버튼 UX 개선 (`frontend/screens/MapView.tsx`)
*   "도보 안내" 및 "차량 안내" 버튼 클릭 시 하단 시트 자동 접기
*   지도가 더 잘 보이도록 UX 개선

```typescript
<button
    onClick={() => {
        fetchRoute('pedestrian');
        setSheetOpen(false); // 지도가 잘 보이도록 시트 접기
    }}
>
    🚶 도보 안내
</button>
```

---

### 10. 🔄 독립적인 삭제 로직 구현 (이전 세션에서 구현됨)

#### A. 백엔드 API 추가 (`backend/api/journey.py`)

**새로운 PATCH 엔드포인트 2종**:

```python
@router.patch("/journey/{sessionId}/unselect")
async def unselect_course(sessionId: str):
    """확정한 코스에서 제거 (is_selected를 false로 변경)"""
    db = await get_database()
    result = await db["user_trip_sessions"].update_one(
        {"sessionId": sessionId},
        {"$set": {"is_selected": False, "updated_at": datetime.utcnow().isoformat()}}
    )
    return {"status": "success", "message": "Course unselected"}

@router.patch("/journey/{sessionId}/remove-timeline")
async def remove_timeline(sessionId: str):
    """타임라인에서 제거 (timeline_generated를 false로 변경)"""
    db = await get_database()
    result = await db["user_trip_sessions"].update_one(
        {"sessionId": sessionId},
        {"$set": {"timeline_generated": False, "updated_at": datetime.utcnow().isoformat()}}
    )
    return {"status": "success", "message": "Timeline removed"}
```

#### B. 프론트엔드 삭제 로직 분리

**HistoryScreen.tsx**:
*   확정한 코스 삭제: `/unselect` 호출 (타임라인에는 유지)
*   히스토리 삭제: `/delete` 호출 (완전 삭제)

**TimelineScreen.tsx**:
*   타임라인 앨범 삭제: `/remove-timeline` 호출 (확정한 코스에는 유지)

---

## 📊 수정된 파일 목록 (2026-02-07)

### Frontend
1. `frontend/features/experience/InvitationPopup.tsx`
   - 초대장 이미지 매핑 (`img` → `imageUrl`)
   - 게스트 저장 방지 로직 추가
   - 게스트 리다이렉트 수정

2. `frontend/screens/MapView.tsx`
   - 하트 아이콘 제거
   - 네비게이션 버튼 UX 개선 (시트 자동 접기)
   - 게스트 체크 로직 확인 (이미 구현됨)

3. `frontend/screens/TimelineScreen.tsx`
   - 게스트 타임라인 접근 차단

4. `frontend/screens/HistoryScreen.tsx`
   - 독립적인 삭제 로직 (이전 세션)

5. `frontend/services/geminiService.ts`
   - 게스트 코스 조회 차단

### Backend
6. `backend/api/journey.py`
   - `/unselect` 엔드포인트 추가 (이전 세션)
   - `/remove-timeline` 엔드포인트 추가 (이전 세션)

### Data
7. `data/invitation_courses.json`
   - 모든 장소에 `img` 필드 추가 (28개 장소)

8. `frontend/public/course_image/`
   - 28개 이미지 파일 복사

---

## 🎯 주요 기능 요약

### ✅ 완료된 기능
1. **초대장 시스템**
   - 실제 이미지 연동
   - 게스트/로그인 사용자 구분 처리

2. **게스트 권한 관리**
   - 게스트는 체험만 가능 (저장 불가)
   - 로그인 사용자만 데이터 저장
   - 타임라인/히스토리 접근 차단

3. **독립적인 삭제 로직**
   - 확정한 코스 ↔ 타임라인 독립 관리
   - Soft delete 방식 적용

4. **UI/UX 개선**
   - 불필요한 버튼 제거
   - 네비게이션 UX 개선

---

## 🚀 다음 단계 권장사항

1. **테스트**
   - 게스트 플로우 전체 테스트
   - 로그인 사용자 플로우 테스트
   - 초대장 → 지도 → 확정 → 타임라인 전체 플로우 검증

2. **코드 정리**
   - Lint 에러 해결
   - 중복 코드 제거
   - 주석 정리

3. **문서화**
   - API 문서 업데이트
   - 사용자 가이드 작성

---

*Generated by Antigravity Assistant (Complete Development Log)*
*Last Updated: 2026-02-07*