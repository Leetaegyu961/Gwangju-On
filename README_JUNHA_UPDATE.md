# 🛠️ Journey Timeline Update Log (2026-02-03)

이 문서는 2026년 2월 3일 오후에 진행된 **타임라인 영구 저장(DB 연동) 및 삭제 기능** 구현에 대한 상세 수정 로그입니다.

---

## 1. 🔙 Backend: `backend/api/journey.py`
기존의 단일 세션 업데이트 로직을 확장하여, 사용자의 **지난 여행 기록(History)을 조회**하고 **삭제**할 수 있는 API 엔드포인트를 추가했습니다.

### ✨ 주요 변경 사항 (Core Changes)

#### A. 여행 히스토리 조회 API (`GET /journey/history/{userId}`)
사용자의 완료된(`COMPLETED`) 여행 기록을 최신순으로 반환합니다.
```python
@router.get("/journey/history/{userId}")
async def get_journey_history(userId: str):
    db = await get_database()
    # 1. userId가 일치하고, status가 'COMPLETED'인 세션만 필터링
    # 2. completed_at 기준 내림차순 정렬 (최신순)
    cursor = db["user_trip_sessions"].find(
        {"userId": userId, "status": "COMPLETED"}
    ).sort("completed_at", -1)
    
    history = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"]) # ObjectId 직렬화 처리
        history.append(doc)
        
    return history
```

#### B. 여행 기록 삭제 API (`DELETE /journey/{sessionId}`)
특정 여행 기록을 영구 삭제합니다.
```python
@router.delete("/journey/{sessionId}")
async def delete_journey(sessionId: str):
    db = await get_database()
    # sessionId를 기준으로 문서 삭제
    result = await db["user_trip_sessions"].delete_one({"sessionId": sessionId})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Journey not found")
        
    return {"status": "success", "message": "Journey deleted"}
```

---

## 2. 🖥️ Frontend: `frontend/screens/TimelineScreen.tsx`
브라우저 로컬 스토리지(휘발성)에 의존하던 로직을 **서버 DB 우선 조회** 로직으로 변경하고, 앨범 삭제 UI를 추가했습니다.

### ✨ 주요 변경 사항 (Core Changes)

#### A. DB 조회 로직 구현 (`fetchHistory`)
- 기존: `localStorage.getItem('current_course')`만 확인.
- 변경: `/api/journey/history/{userId}` API를 먼저 호출하여 DB 데이터를 `albums` 상태에 매핑.
- **Fallback**: DB에 데이터가 없거나 서버 오류 시 로컬 스토리지를 확인하도록 안전장치 마련.

```typescript
// [Updated] Fetch Journey History from DB
const fetchHistory = async () => {
    const userId = localStorage.getItem('temp_user_id');
    // ... API 호출 ...
    const res = await fetch(`${API_URL}/api/journey/history/${userId}`);
    if (res.ok) {
        const data = await res.json();
        // Server Data -> UI Album Model Mapping
        const mappedAlbums = data.map((session: any) => ({
            id: session.sessionId,
            title: session.ai_summary || "나만의 감성 광주 여행",
            spots: session.album_data || [], // 저장된 장소 리스트
            isNew: false // DB에서 불러온 데이터는 New 배지 제거
            // ... 기타 필드 매핑 ...
        }));
        setAlbums(mappedAlbums);
    }
    // ... Fallback Logic ...
};
```

#### B. 앨범 삭제 기능 (`handleDeleteAlbum`)
- **UI**: 앨범 카드 우상단에 `Trash2`(쓰레기통) 아이콘 버튼 추가.
- **Logic**: 삭제 확인(`confirm`) 후 API 호출 (`DELETE /api/journey/{id}`).
- **UX**: 삭제 성공 시 화면에서 즉시 카드를 제거(Filter)하여 반응성 향상.

```typescript
<button 
    onClick={(e) => handleDeleteAlbum(e, album.id)}
    className="absolute top-2 right-2 z-50 p-2 text-gray-300 hover:text-red-500 ..."
    title="앨범 삭제"
>
    <Trash2 size={16} />
</button>
```

---

## 3. 👤 마이페이지 UI 개선 (`frontend/screens/MyPage.tsx`)
사용자의 현재 프로필 정보(나이, 성별)를 **시각적으로 확인**할 수 있도록 UI를 개선했습니다.

### ✨ 주요 변경 사항 (Core Changes)
- **프로필 배지(Badge) 추가**: 사용자 이름 하단에 `[20대]` `[여성]`과 같은 형태의 태그를 추가하여, 현재 설정된 Demographics 정보를 직관적으로 보여줍니다.
- **실시간 반영**: 설정 팝업에서 정보를 수정하고 저장하면, DB 업데이트와 동시에 배지 내용도 즉시 변경됩니다.

```typescript
{/* User Profile Badges (Age/Gender) */}
<div className="flex gap-2 justify-center mb-3">
    {profile?.age && (
        <span className="px-2.5 py-0.5 bg-blue-50 text-blue-600 text-[10px] font-bold rounded-full border border-blue-100 shadow-sm">
            {profile.age}
        </span>
    )}
    {profile?.gender && (
        <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-500 text-[10px] font-bold rounded-full border border-indigo-100 shadow-sm">
            {profile.gender}
        </span>
    )}
</div>
```

---

---

## 4. 🎨 Timeline UI 전면 리뉴얼 & 기능 고도화
**(2026-02-03 17:30 Update)**

앱의 전반적인 디자인 통일성을 위해 `TimelineScreen`의 UI를 **Blue Theme & Mascot Identity**로 전면 개편하고, 사용자 참여형 기능을 추가했습니다.

### ✨ 주요 변경 사항 (Core Changes)

#### A. 디자인 테마 통일 (`Blue & Mascot Style`)
- **Background**: 기존 베이지색 배경을 **밝은 블루톤(#F5F8FF)**으로 변경하고, **마스코트 캐릭터 애니메이션**을 추가하여 화사한 분위기 연출.
- **Header**: `MyPage`와 동일한 스타일(`Travel Log` 태그, 타이포그래피) 적용.
- **Album Card**: 카드 그림자 및 테두리를 블루 계열(`border-blue-50`, `shadow-blue-100`)로 변경하여 일관성 유지.
- **Grid Layout**: 사진이 2장일 때 `aspect-square`로 가로 배치되도록 개선, 4장일 때 비율 최적화.

#### B. 사용자 코멘트 기록 기능 (`User Editable Description`)
상세 타임라인에서 AI가 작성한 기본 장소 설명을 **사용자가 직접 편집**할 수 있는 기능을 추가했습니다.
- **Textarea 도입**: 설명 텍스트를 클릭하면 수정 모드로 전환.
- **Fallback Logic**: 사용자가 내용을 입력하지 않으면 **기존 AI 요약 설명**이 기본값으로 표시됨.
- **State Persistence**: 수정된 내용은 세션 내에서 유지됨.

#### C. Backend Interaction (`MapView.tsx` -> `DB`)
코스 확정(`handleConfirmCourse`) 시, 기존 로컬 스토리지 저장 방식에서 **DB 영구 저장 API 호출**로 로직을 강화했습니다.
```typescript
// MapView.tsx
await fetch(`${API_URL}/api/journey/save-final`, {
    method: 'POST',
    body: JSON.stringify({ userId, pickedPlaces: finalSpots, aiSummary })
});
```

#### D. Bug Fixes
- `onClose` Prop 미전달로 인한 **닫기 버튼 오작동 수정** (`router.back()` 연결).
- 리스트/디테일 뷰 전환 시 불필요한 레이아웃 꼬임 해결.

---

## 5. 🛠️ Bug Fixes & UX Performance Tuning
**(2026-02-04 Update)**

사용자 피드백을 반영하여 **타임라인 UI의 사용성**을 대폭 개선하고, **API 호출 최적화** 및 **버그 수정**을 완료했습니다.

### ✨ 주요 변경 사항 (Core Changes)

#### A. 장소 설명 편집 위치 변경 (`TimelineScreen.tsx`)
- **변경 전**: 앨범 상세 보기(Modal) 슬라이드 내에서 설명을 수정.
- **변경 후**: **리스트 뷰(List View)**의 사진 업로드 영역 상단으로 설명 입력창(`textarea`)을 이동.
- **이유**: 사진을 올리면서 바로 설명을 적는 것이 자연스러운 동작(UX)이므로 위치를 재배치.
- **Modal View**: 앨범 카드는 **읽기 전용(Read-Only)** 뷰로 변경하여, 최종 결과물을 감상하는 용도로 명확히 구분.

#### B. 앨범 카드 텍스트 렌더링 수정 (`TimelineScreen.tsx`)
- **Issue**: 앨범 카드 모달에서 텍스트 영역의 높이가 0으로 잡혀 글자가 보이지 않는 현상.
- **Fix**: 
    - 레이아웃을 `Relative` + `Flex` 구조에서 **`Absolute Positioning`** 구조로 변경하여 텍스트 박스를 강제로 확장.
    - 데이터가 비어있을 경우(빈 문자열 등), 공백 대신 **기본 문구**나 **기존 장소 설명(`spot.desc`)**이 우선적으로 표시되도록 Fallback 로직 강화.
    - **디자인 강화**: 글자색을 진하게(`text-gray-900`) 하고 가시성을 높임.

#### C. 지도 API 호출 최적화 (`TimelineScreen.tsx`)
- **Issue**: 댓글 입력, 사진 업로드 등으로 상태가 변할 때마다 `/api/maps/static` API가 불필요하게 반복 호출되어 서버 로그가 폭주하는 문제.
- **Fix**: **좌표(`lat`, `lng`)가 실제로 변경된 경우에만** API를 호출하도록 비교 로직(Memoization)을 추가하여 서버 부하 감소.

#### D. 코스 확정 UX 개선 (`MapView.tsx`)
- **Issue**: "이 코스로 결정하기" 버튼 클릭 후, 화면 이동이 없어 사용자가 완료 여부를 모른 채 오류로 오인하거나 불안해함.
- **Fix**: `save-final` 완료 후 **즉시 타임라인 화면으로 이동(`router.push('/timeline')`)**하도록 로직 추가하여 UX 흐름을 명확히 함.

---
*Last Updated: 2026-02-04 17:35*