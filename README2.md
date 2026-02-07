# 여행초대장 기능 통합


---

## 1. Backend 수정 사항

### 1-1. `backend/api/session.py` (신규 생성)
서버 실행 오류(`NameError: name 'session' is not defined`)를 해결하고, 초대장 코스를 사용자 세션에 적용하는 기능을 구현하기 위해 새로 생성된 파일입니다.

```python
from fastapi import APIRouter, HTTPException, Body
from backend.db import get_database
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/session", tags=["Session"])

@router.post("/apply-invitation/{user_id}")
async def apply_invitation_to_session(user_id: str, payload: Dict[str, Any] = Body(...)):
    """
    초대장의 코스 데이터(album_data)를 
    사용자의 현재 세션(user_trip_sessions)에 덮어씌우거나 업데이트합니다.
    """
    db = await get_database()
    album_data = payload.get("album_data", [])
    
    if not album_data:
        raise HTTPException(status_code=400, detail="No album data provided")

    # 1. Update/Upsert Session
    # user_trip_sessions 컬렉션에서 user_id에 해당하는 status=IN_PROGRESS 세션을 찾아서 업데이트
    
    # Check for active session
    active_session = await db["user_trip_sessions"].find_one({
        "user_id": user_id,
        "status": "IN_PROGRESS"
    })
    
    new_context = {
        "user_id": user_id,
        "status": "IN_PROGRESS",
        "current_course": album_data, # 코스 주입
        "last_activity_at": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat()
    }

    if active_session:
        # Update existing
        await db["user_trip_sessions"].update_one(
            {"_id": active_session["_id"]},
            {"$set": {
                "current_course": album_data,
                "last_activity_at": datetime.now().isoformat()
            }}
        )
    else:
        # Create new session if not exists
        await db["user_trip_sessions"].insert_one(new_context)
    
    return {"message": "Session updated with invitation course", "course_len": len(album_data)}
```

### 1-2. `backend/main.py` (Import 추가)
라우터 등록 부분에 `session` 모듈을 추가했습니다.

```python
# 기존 코드의 include_router 섹션 수정
from backend.api import user, photo, place_info, tmap, auth, journey, tasting_note, maps, session

# ... (기존 라우터들)
app.include_router(session.router, prefix="/api")
```

---

## 2. Frontend 수정 사항

### 2-1. `frontend/screens/MyPage.tsx` (UI 원상 복구 및 기능 통합)
기존의 파란색 테마/마스코트 디자인으로 UI를 복구하고, 찜한 코스 개수 표시 및 연동 기능을 통합했습니다.

```tsx
"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { History, Bookmark, Settings, ChevronRight, Sparkles, TrendingUp, User, LogOut, Brain, ArrowLeft } from 'lucide-react';
import { GeminiService } from '../services/geminiService';
import { SavedCourse } from '../types';
import { AgentContextDashboard } from '../features/dashboard/AgentContextDashboard';
import GuestSettingsModal from '../components/user/GuestSettingsModal';
import UserSettingsModal from '../components/user/UserSettingsModal';
import { motion } from 'framer-motion';

const aiService = new GeminiService();
// Fix for React 19 type mismatch
const MotionDiv = motion.div as any;

/**
 * [Prompt 7: My Page Screen Refinement]
 */
export const MyPage = () => {
   const router = useRouter();
   const [savedCourses, setSavedCourses] = useState<SavedCourse[]>([]);
   const [profile, setProfile] = useState<any>(null);
   const [statistics, setStatistics] = useState<any>(null);
   const [isDashboardOpen, setIsDashboardOpen] = useState(false);
   const [showGuestModal, setShowGuestModal] = useState(false);
   const [showUserModal, setShowUserModal] = useState(false);
   const [userWishlist, setUserWishlist] = useState<any[]>([]);

   useEffect(() => {
      if (typeof window !== 'undefined') {
         const saved = localStorage.getItem('user_profile');
         if (saved) {
            setProfile(JSON.parse(saved));
         }
      }

      aiService.getUserProfile().then(p => {
         if (p) {
            setProfile(p);
            localStorage.setItem('user_profile', JSON.stringify(p));

            // Fetch Wishlist from DB
            const userId = p.id || localStorage.getItem('temp_user_id');
            if (userId) {
               fetch(`http://localhost:8000/api/journey/wishlist/${userId}`)
                  .then(res => res.json())
                  .then(data => {
                     if (data.wishlist) setUserWishlist(data.wishlist);
                  });
            }
         }
      });
      aiService.getCourses().then(setSavedCourses);
      aiService.getUserStatistics().then(setStatistics);
   }, []);

   const handleLogout = () => {
      if (confirm('로그아웃 하시겠습니까?')) {
         localStorage.removeItem('access_token');
         localStorage.removeItem('temp_user_id');
         localStorage.removeItem('user_profile');
         localStorage.removeItem('courses');
         localStorage.removeItem('current_course');
         router.push('/login');
      }
   };

   const userName = profile?.name || 'GUEST';
   const userImage = (profile && profile.picture && profile.picture !== "")
      ? profile.picture
      : "https://ui-avatars.com/api/?name=Guest&background=EFF6FF&color=3B82F6&bold=true&length=1"; // Blue theme avatar
   const tripCount = savedCourses.length;

   return (
      <div className="min-h-screen bg-[#F5F8FF] pb-40 overflow-y-auto font-['Inter'] hide-scrollbar relative">
         <AgentContextDashboard isOpen={isDashboardOpen} onClose={() => setIsDashboardOpen(false)} />

         {/* Mascot Decoration (Background) */}
         <div className="absolute top-20 right-[-20px] w-32 opacity-20 pointer-events-none animate-float">
            <img src="/mascot_full.png" alt="Mascot" className="w-full" />
         </div>
         <div className="absolute bottom-40 left-[-30px] w-40 opacity-10 pointer-events-none rotate-12">
            <img src="/mascot_full.png" alt="Mascot" className="w-full grayscale" />
         </div>

         {/* Top Navigation */}
         <div className="flex justify-between items-center px-6 pt-6 relative z-10 transition-all">
            <button
               onClick={() => router.back()}
               className="w-10 h-10 bg-white border border-blue-50 rounded-full flex items-center justify-center text-gray-400 hover:text-[#3B82F6] hover:border-blue-100 transition-colors shadow-sm"
            >
               <ArrowLeft size={20} />
            </button>
            <button
               onClick={() => {
                  if (!profile || !profile.name) {
                     setShowGuestModal(true);
                  } else {
                     setShowUserModal(true);
                  }
               }}
               className="flex items-center gap-2 px-4 py-2 bg-white border border-blue-50 rounded-full text-gray-500 hover:text-[#3B82F6] hover:bg-blue-50 hover:border-blue-100 transition-all shadow-sm active:scale-95 group"
            >
               <Settings size={18} className="group-hover:rotate-45 transition-transform duration-500" />
               <span className="text-xs font-bold">설정</span>
            </button>
         </div>

         {/* Profile Header */}
         <header className="pt-10 px-8 pb-12 flex flex-col items-center relative z-10">
            <MotionDiv
               initial={{ scale: 0.9, opacity: 0 }}
               animate={{ scale: 1, opacity: 1 }}
               transition={{ duration: 0.5 }}
               className="relative mb-8"
            >
               <div className="w-32 h-32 rounded-full overflow-hidden shadow-2xl ring-4 ring-white border border-blue-100 relative bg-white">
                  <img src={userImage} className="w-full h-full object-cover" alt="Profile" />
               </div>
               <div className="absolute -bottom-2 -right-2 bg-[#3B82F6] w-10 h-10 rounded-full flex items-center justify-center text-white shadow-lg border-4 border-white">
                  <Sparkles size={16} fill="white" />
               </div>
            </MotionDiv>

            <div className="text-center mb-8">
               <h2 className="text-2xl font-black text-gray-800 mb-2">{userName}</h2>

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
               <div className="inline-flex items-center gap-2 bg-white px-4 py-1.5 rounded-full border border-blue-100 shadow-sm">
                  <TrendingUp size={14} className="text-[#3B82F6]" />
                  <p className="text-xs font-bold text-gray-500">나의 여행 횟수: <span className="text-[#3B82F6]">{tripCount}회</span></p>
               </div>
            </div>

            {/* Tags */}
            <div className="flex gap-2 flex-wrap justify-center max-w-xs mb-8">
               {(statistics?.top_themes?.length > 0 ? statistics.top_themes.map((t: any) => `#${t.theme}`) : ['#취향분석중', '#여행시작', '#나만의코스']).map((tag: string, i: number) => (
                  <MotionDiv
                     key={i}
                     initial={{ opacity: 0, y: 10 }}
                     animate={{ opacity: 1, y: 0 }}
                     transition={{ delay: i * 0.1 }}
                     className="bg-white px-4 py-2 rounded-xl border border-blue-50 text-xs font-bold text-gray-600 shadow-sm hover:text-[#3B82F6] hover:border-blue-100 transition-colors cursor-default"
                  >
                     {tag}
                  </MotionDiv>
               ))}
            </div>

            {/* Stats Cards */}
            {statistics && (
               <MotionDiv
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="w-full max-w-sm"
               >
                  <div className="bg-white p-5 rounded-3xl shadow-lg shadow-blue-100/50 border border-blue-100 grid grid-cols-2 gap-4 relative overflow-hidden group">
                     {/* Decorative bg */}
                     <div className="absolute top-0 right-0 w-24 h-24 bg-blue-50 rounded-full blur-3xl -z-10 opacity-60 group-hover:bg-blue-100 transition-colors"></div>

                     <div className="text-center">
                        <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">평균 여행 예산</p>
                        <p className="text-lg font-black text-gray-800">{statistics.average_budget}만원</p>
                     </div>
                     <div className="text-center border-l border-blue-50">
                        <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">가성비 민감도</p>
                        <p className="text-lg font-black text-[#3B82F6]">{statistics.price_sensitivity_label}</p>
                     </div>
                  </div>
               </MotionDiv>
            )}
         </header>

         {/* Menu Section */}
         <section className="px-6 space-y-4 max-w-md mx-auto relative z-10">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider ml-4 mb-2">My Menu</h3>

            <MotionDiv initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}>
               <button
                  onClick={() => router.push('/history')}
                  className="w-full flex items-center justify-between p-5 bg-white hover:bg-blue-50/50 border border-transparent hover:border-blue-100 text-gray-800 rounded-3xl transition-all group shadow-sm hover:shadow-md"
               >
                  <div className="flex items-center gap-4 font-bold text-sm">
                     <div className="p-3 bg-gray-50 rounded-2xl text-gray-600 group-hover:bg-[#3B82F6] group-hover:text-white transition-all">
                        <History size={20} />
                     </div>
                     이전 여행 기록
                  </div>
                  <ChevronRight size={18} className="text-gray-300 group-hover:text-[#3B82F6] group-hover:translate-x-1 transition-transform" />
               </button>
            </MotionDiv>

            <MotionDiv initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }}>
               <button 
                  onClick={() => router.push('/wishlist')}
                  className="w-full flex items-center justify-between p-5 bg-white hover:bg-blue-50/50 border border-transparent hover:border-blue-100 text-gray-800 rounded-3xl transition-all group shadow-sm hover:shadow-md">
                  <div className="flex items-center gap-4 font-bold text-sm">
                     <div className="p-3 bg-gray-50 rounded-2xl text-gray-600 group-hover:bg-[#3B82F6] group-hover:text-white transition-all">
                        <Bookmark size={20} />
                     </div>
                     찜한 코스 {userWishlist.length > 0 && <span className="text-[#3B82F6] ml-1">({userWishlist.length})</span>}
                  </div>
                  <ChevronRight size={18} className="text-gray-300 group-hover:text-[#3B82F6] group-hover:translate-x-1 transition-transform" />
               </button>
            </MotionDiv>

            <MotionDiv initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 }}>
               <button
                  onClick={() => setIsDashboardOpen(true)}
                  className="w-full flex items-center justify-between p-5 bg-white hover:bg-blue-50/50 border border-transparent hover:border-blue-100 text-gray-800 rounded-3xl transition-all group shadow-sm hover:shadow-md"
               >
                  <div className="flex items-center gap-4 font-bold text-sm">
                     <div className="p-3 bg-gray-50 rounded-2xl text-gray-600 group-hover:bg-[#3B82F6] group-hover:text-white transition-all">
                        <Brain size={20} />
                     </div>
                     에이전트 대시보드
                  </div>
                  <ChevronRight size={18} className="text-gray-300 group-hover:text-[#3B82F6] group-hover:translate-x-1 transition-transform" />
               </button>
            </MotionDiv>
         </section>

         <GuestSettingsModal
            isOpen={showGuestModal}
            onClose={() => setShowGuestModal(false)}
            onLogout={handleLogout}
         />
         <UserSettingsModal
            isOpen={showUserModal}
            onClose={() => setShowUserModal(false)}
            onLogout={handleLogout}
            userId={profile?.id}
            initialAge={profile?.age}
            initialGender={profile?.gender}
            onProfileUpdate={(age, gender) => {
               const newProfile = { ...profile, age, gender };
               setProfile(newProfile);
               localStorage.setItem('user_profile', JSON.stringify(newProfile));
            }}
         />
      </div>
   );
};
```

### 2-2. `frontend/screens/WishlistScreen.tsx` (React 19 호환성 패치)
`framer-motion`과 React 19 간의 타입 충돌 해결을 위해 `MotionDiv`를 도입했습니다.

```tsx
"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, Calendar, ChevronRight, Share2, ArrowLeft, Bookmark, Wand2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Fix for React 19 type mismatch
const MotionDiv = motion.div as any;

export default function WishlistScreen() {
    const router = useRouter();
    // ... (상태 관리 로직 동일)

    // 리스트 렌더링 예시 (motion.div 대신 MotionDiv 사용)
    return (
        <div className="min-h-screen bg-[#FDFBF7] font-['Inter'] relative pb-32">
             {/* ... */}
                    <div className="space-y-6">
                        {wishlist.map((item, index) => (
                            <MotionDiv
                                key={item.id || index}
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: index * 0.05 }}
                                onClick={() => {
                                    setSelectedItem(item);
                                    setViewMode('detail');
                                }}
                                className="... (생략)"
                            >
                                {/* ... Card Content ... */}
                            </MotionDiv>
                        ))}
                    </div>
             {/* ... */}
        </div>
    );
}
```

---

# 2026-02-04 추가 업데이트 (초대장/탐색 UX 개선 및 버그 수정)

이 업데이트는 '초대장 팝업' 기능을 실제 데이터와 연동하고, '장소 탐색' 경험을 개선하며, 지도 및 설문 화면의 버그를 수정한 내역입니다.

## 3. 초대장 및 코스 데이터 연동 (InvitationPopup)

### 3-1. rontend/features/experience/InvitationPopup.tsx
*   **데이터 연동**: 기존 하드코딩된 데이터를 제거하고 data/invitation_courses.json을 직접 import하여 사용하도록 수정했습니다.
*   **랜덤 추천**: 팝업이 뜰 때마다 7개의 코스 중 하나를 랜덤으로 제안하는 로직을 추가했습니다.
*   **이미지 매핑**: rontend/utils/courseImages.ts를 활용하여 장소 이름과 카테고리에 맞는 고화질 Unsplash 이미지를 자동으로 매핑하도록 개선했습니다.
*   **안정적인 이미지**: Unsplash Source API 이슈를 해결하기 위해 고정된 고품질 이미지 ID로 링크를 교체했습니다.

## 4. 장소 탐색 화면 리팩토링 및 UX 개선 (Discovery)

### 4-1. rontend/screens/DiscoveryScreen.tsx (신규 분리)
*   **구조 개선**: 기존 pp/discovery/page.tsx에 혼재되어 있던 비즈니스 로직과 UI 코드를 screens/DiscoveryScreen.tsx로 분리하여 유지보수성을 높였습니다. pp/discovery/page.tsx는 이제 단순 래퍼 역할만 합니다.
*   **UX 개선 (종료 버튼)**: 우측 상단의 'X' 버튼을 누르면 메인 홈이 아닌 **설문조사 페이지(/survey)로 돌아가도록** 수정하여 사용 흐름을 자연스럽게 만들었습니다.

### 4-2. rontend/features/experience/PlaceInteractiveCard.tsx
*   **버튼 변경**: '다른 장소 물색'이라는 모호한 버튼명을 **'다음 장소 보기'**로 변경하고, 불필요한 알림창(lert)을 제거하여 더 부드러운 카드 넘김 경험을 제공합니다.
*   **종료 핸들러**: onClose prop을 추가하여 상위 컴포넌트(DiscoveryScreen)에서 종료 동작을 제어할 수 있게 했습니다.

## 5. 버그 수정 및 최적화

### 5-1. rontend/screens/MapView.tsx (안전성 강화)
*   **데이터 매핑 오류 수정**: 코스 데이터(places)가 없거나 배열이 아닐 경우 undefined.map 에러가 발생하는 것을 방지하기 위해 방어 코드(ensureIds 함수 내)를 추가했습니다.
*   **이미지 로드 오류 수정**: 이미지 onError 핸들러에서 parentElement가 
ull일 때 발생하던 크래시(TypeError: Cannot set properties of null)를 해결했습니다.

### 5-2. rontend/screens/SurveyScreen.tsx (UI 간소화)
*   **사이드 메뉴 제거**: 설문조사 화면에서 불필요했던 햄버거 메뉴와 '카테고리 탐색 사이드 모달' 기능을 제거하여 화면을 깔끔하게 정리하고 에러 가능성을 줄였습니다.
*   **중복 Import 제거**: 코드 리팩토링 과정에서 발생했던 중복 import 및 린트 오류를 해결했습니다.


---

# 2026-02-04 추가 업데이트 (테이스팅 노트 연결 및 사용 흐름 개선)

타임라인에서 여행을 마치고 테이스팅 노트(총평)를 작성하는 흐름을 완성하고, 불필요한 메인 화면을 정리하여 앱의 사용성을 높였습니다.

## 6. 테이스팅 노트(Tasting Note) 연결 및 흐름 개선

### 6-1. rontend/screens/TimelineScreen.tsx (진입점 추가)
*   **여행 종료 버튼**: 상세 타임라인 뷰 우측 하단에 '📝 여행 종료 및 총평' 버튼을 추가했습니다.
*   **라우팅 연결**: 버튼 클릭 시 /tasting-note 페이지로 이동하여 사용자가 여행에 대한 최종 리뷰를 남길 수 있게 했습니다.

### 6-2. rontend/screens/TastingNoteScreen.tsx (종료 흐름 수정)
*   **작성 완료 후 이동 경로 변경**: 기존에는 작성 완료 후 /home으로 이동했으나, 해당 페이지가 삭제됨에 따라 **/map (지도)**으로 이동하도록 수정했습니다. 이로써 여행이 끝난 후 다시 지도로 돌아와 다음 여정을 준비하는 자연스러운 흐름이 만들어졌습니다.

### 6-3. rontend/app/home & HomeScreen.tsx (레거시 제거)
*   **홈 화면 삭제**: 현재 로그인 후 메인 화면 역할은 /map이 담당하고 있어, 더 이상 사용하지 않고 중복되는 /home 경로와 관련 컴포넌트를 삭제하여 프로젝트 구조를 정리했습니다.

## 7. 백엔드 데이터 저장 확인

*   **저장 위치**: 테이스팅 노트 데이터는 백엔드 MongoDB의 **	asting_notes** 컬렉션에 저장됩니다.
*   **세션 상태 관리**: 노트 저장 시 해당 여행 세션(user_trip_sessions)의 상태가 COMPLETED로 변경되어 여행 완료 처리가 정상적으로 이루어짐을 확인했습니다.

