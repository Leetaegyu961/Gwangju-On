
"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { History, Bookmark, Settings, ChevronRight, Sparkles, TrendingUp, User, LogOut, Brain, Share2 } from 'lucide-react';
import { GeminiService } from '../services/geminiService';
import { SavedCourse } from '../types';
import { AgentContextDashboard } from '@/features/dashboard/AgentContextDashboard';
import GuestSettingsModal from '../components/user/GuestSettingsModal';
import UserSettingsModal from '../components/user/UserSettingsModal';

const aiService = new GeminiService();

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
      // 1. Load from LocalStorage immediately on mount preventing hydration mismatch
      if (typeof window !== 'undefined') {
         const saved = localStorage.getItem('user_profile');
         if (saved) {
            setProfile(JSON.parse(saved));
         }
      }

      // 2. Fetch fresh Profile from server
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
      // Fetch Courses
      aiService.getCourses().then(setSavedCourses);
      // Fetch Statistics
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
      : "https://ui-avatars.com/api/?name=Guest&background=F3F4F6&color=9CA3AF&bold=true&length=1";
   const tripCount = savedCourses.length;

   return (
      <div className="min-h-screen bg-white pb-40 overflow-y-auto font-['Inter'] hide-scrollbar relative">
         <AgentContextDashboard isOpen={isDashboardOpen} onClose={() => setIsDashboardOpen(false)} />

         {/* Top Navigation / Settings */}
         <button
            onClick={() => {
               if (!profile || !profile.name) {
                  setShowGuestModal(true);
               } else {
                  setShowUserModal(true);
               }
            }}
            className="absolute top-8 right-8 z-10 flex items-center gap-2 px-4 py-2.5 bg-white/80 backdrop-blur-md border border-gray-100 rounded-full text-gray-400 hover:text-blue-500 hover:bg-blue-50 hover:border-blue-100 transition-all shadow-sm active:scale-95 group"
            aria-label="설정"
         >
            <Settings size={16} className="group-hover:stroke-blue-500 transition-colors" />
            <span className="text-xs font-black tracking-tight">설정</span>
         </button>

         {/* Profile Header per Prompt 7 */}
         <header className="pt-24 px-10 pb-16 flex flex-col items-center bg-gradient-to-b from-blue-50/50 to-white rounded-b-[4rem]">
            <div className="relative mb-10">
               <div className="w-32 h-32 rounded-full overflow-hidden shadow-2xl ring-8 ring-white">
                  <img src={userImage} className="w-full h-full object-cover" alt="Profile" />
               </div>
               <div className="absolute -bottom-1 -right-1 bg-[#0066FF] w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-blue-200 border-4 border-white">
                  <Sparkles size={20} />
               </div>
            </div>

            <div className="text-center mb-10">
               <h2 className="text-3xl font-black text-gray-900 tracking-tighter mb-2 italic uppercase">{userName}</h2>
               <div className="flex items-center gap-2 bg-white px-5 py-2 rounded-2xl border border-gray-100 shadow-sm">
                  <TrendingUp size={14} className="text-[#0066FF]" />
                  <p className="text-sm font-black text-gray-400 uppercase tracking-widest">나의 여행 횟수: <span className="text-[#0066FF]">{tripCount}회</span></p>
               </div>
            </div>

            {/* Taste Keyword cluster per Prompt 7 */}
            <div className="flex gap-2.5 flex-wrap justify-center max-w-[300px] mb-8">
               {(statistics?.top_themes?.length > 0 ? statistics.top_themes.map((t: any) => `#${t.theme}`) : ['#취향분석중', '#여행을시작해보세요', '#나만의코스']).map((tag: string, i: number) => (
                  <span key={i} className="bg-white px-5 py-2.5 rounded-2xl border border-gray-100 text-sm font-black text-gray-500 shadow-sm hover:shadow-md transition-all cursor-default animate-fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
                     {tag}
                  </span>
               ))}
            </div>

            {/* Statistics Section (New) */}
            {statistics && (
               <div className="w-full max-w-sm px-4">
                  <div className="bg-white p-5 rounded-[2rem] shadow-sm border border-gray-100 grid grid-cols-2 gap-4">
                     <div className="text-center">
                        <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">평균 여행 예산</p>
                        <p className="text-lg font-black text-gray-800">{statistics.average_budget}만원</p>
                     </div>
                     <div className="text-center border-l border-gray-100">
                        <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">가성비 민감도</p>
                        <p className="text-lg font-black text-[#0066FF]">{statistics.price_sensitivity_label}</p>
                     </div>
                  </div>
               </div>
            )}
         </header>

         {/* Menu Section per Prompt 7 */}
         <section className="px-10 py-12 space-y-6">
            <h3 className="text-sm font-black text-gray-300 uppercase tracking-[0.3em] mb-4">Account Menu</h3>
            <div className="grid grid-cols-1 gap-4">
               <button
                  onClick={() => router.push('/timeline')}
                  className="flex items-center justify-between p-8 bg-white hover:bg-blue-50/30 border border-gray-100 hover:border-blue-200 text-gray-900 rounded-[2.5rem] transition-all group shadow-sm hover:shadow-xl active:scale-[0.98]">
                  <div className="flex items-center gap-5 font-black text-base tracking-tight">
                     <div className="p-4 bg-gray-50 rounded-2xl shadow-sm text-blue-500 group-hover:bg-[#0066FF] group-hover:text-white transition-all"><History size={22} /></div>
                     이전 여행 기록 (추억 앨범)
                  </div>
                  <ChevronRight size={20} className="text-gray-300 group-hover:translate-x-1 transition-transform" />
               </button>

               <div className="space-y-4">
                  <div className="flex items-center justify-between mb-2">
                     <h3 className="text-sm font-black text-gray-300 uppercase tracking-[0.3em]">Pre-travel Albums</h3>
                  </div>

                  {/* 찜한 코스 진입 버튼 (ProV3 스타일 원상 복구) */}
                  <button
                     onClick={() => router.push('/wishlist')}
                     className="w-full flex items-center justify-between p-8 bg-white hover:bg-red-50/30 border border-gray-100 hover:border-red-200 text-gray-900 rounded-[2.5rem] transition-all group shadow-sm hover:shadow-xl active:scale-[0.98]">
                     <div className="flex items-center gap-5 font-black text-base tracking-tight">
                        <div className="p-4 bg-gray-50 rounded-2xl shadow-sm text-red-500 group-hover:bg-red-500 group-hover:text-white transition-all"><Bookmark size={22} /></div>
                        나의 찜한 코스 {userWishlist.length > 0 && `(${userWishlist.length})`}
                     </div>
                     <ChevronRight size={20} className="text-gray-300 group-hover:translate-x-1 transition-transform" />
                  </button>
               </div>

               <button
                  onClick={() => setIsDashboardOpen(true)}
                  className="flex items-center justify-between p-8 bg-white hover:bg-purple-50/30 border border-gray-100 hover:border-purple-200 text-gray-900 rounded-[2.5rem] transition-all group shadow-sm hover:shadow-xl active:scale-[0.98]">
                  <div className="flex items-center gap-5 font-black text-base tracking-tight">
                     <div className="p-4 bg-white rounded-2xl shadow-sm text-purple-500 group-hover:bg-purple-500 group-hover:text-white transition-all"><Brain size={22} /></div>
                     에이전트 컨텍스트 (Dashboard)
                  </div>
                  <ChevronRight size={20} className="text-gray-300 group-hover:translate-x-1 transition-transform" />
               </button>
            </div>
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
