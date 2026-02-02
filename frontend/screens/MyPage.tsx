
"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { History, Bookmark, Settings, ChevronRight, Sparkles, TrendingUp, User, LogOut } from 'lucide-react';
import { GeminiService } from '../services/geminiService';
import { SavedCourse } from '../types';

const aiService = new GeminiService();

/**
 * [Prompt 7: My Page Screen Refinement]
 */
export const MyPage = () => {
   const router = useRouter();
   const [savedCourses, setSavedCourses] = useState<SavedCourse[]>([]);
   const [profile, setProfile] = useState<any>(null);

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
         }
      });
      // Fetch Courses
      aiService.getCourses().then(setSavedCourses);
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
      <div className="min-h-screen bg-[#FDFBF7] pb-40 overflow-y-auto font-['Inter'] hide-scrollbar relative">
         {/* Top Navigation / Logout */}
         <button
            onClick={handleLogout}
            className="absolute top-6 right-6 z-20 flex items-center gap-2 px-4 py-2 bg-white/80 backdrop-blur-sm border border-orange-100 rounded-full text-gray-500 hover:text-red-500 hover:bg-red-50 hover:border-red-100 transition-all shadow-sm active:scale-95 group"
            aria-label="로그아웃"
         >
            <LogOut size={16} className="group-hover:stroke-red-500 transition-colors" />
            <span className="text-xs font-bold">로그아웃</span>
         </button>

         {/* Profile Header */}
         <header className="pt-24 pb-12 px-6 flex flex-col items-center bg-white rounded-b-[3rem] shadow-sm border-b border-gray-50 relative overflow-hidden">
            {/* Background Decor */}
            <div className="absolute top-0 left-0 w-full h-40 bg-gradient-to-b from-orange-50/50 to-transparent pointer-events-none" />

            <div className="relative mb-6 z-10">
               <div className="w-28 h-28 rounded-full overflow-hidden shadow-lg border-4 border-white ring-1 ring-gray-100 relative bg-gray-50">
                  {/* If userImage is default, maybe show mascot? For now keeping userImage logic */}
                  <img src={userImage} className="w-full h-full object-cover" alt="Profile" />
               </div>
               <div className="absolute -bottom-2 -right-2 bg-white p-1.5 rounded-full shadow-md border border-gray-100">
                  <div className="bg-[#FF6B00] w-8 h-8 rounded-full flex items-center justify-center text-white">
                     <Sparkles size={16} />
                  </div>
               </div>
            </div>

            <div className="text-center mb-8 z-10">
               <h2 className="text-2xl font-bold text-gray-800 mb-2">{userName}님, 안녕하세요!</h2>
               <div className="inline-flex items-center gap-2 bg-[#F8FAFC] px-4 py-2 rounded-full border border-gray-100">
                  <span className="w-2 h-2 rounded-full bg-[#0066FF]" />
                  <p className="text-sm font-medium text-gray-500">
                     나의 여행 횟수 <span className="text-[#0066FF] font-bold ml-1">{tripCount}회</span>
                  </p>
               </div>
            </div>

            {/* Taste Keywords */}
            <div className="flex gap-2 flex-wrap justify-center max-w-[320px] z-10">
               {['#힐링', '#로컬맛집', '#빈티지', '#사진공유', '#도보여행'].map((tag, i) => (
                  <span key={i} className="bg-white px-4 py-2 rounded-full border border-orange-100/50 text-xs font-bold text-gray-600 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all cursor-default animate-fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
                     {tag}
                  </span>
               ))}
            </div>
         </header>

         {/* Menu Section */}
         <section className="px-6 py-10 space-y-6">
            <div className="px-2 flex items-center gap-2 mb-2">
               <h3 className="text-lg font-bold text-gray-800">계정 관리</h3>
               <div className="h-px flex-1 bg-gray-100" />
            </div>

            <div className="grid grid-cols-1 gap-4">
               <button
                  onClick={() => router.push('/history')}
                  className="flex items-center justify-between p-6 bg-white border border-gray-100 text-gray-800 rounded-3xl transition-all group shadow-sm hover:shadow-md hover:border-blue-100 active:scale-[0.98]"
               >
                  <div className="flex items-center gap-4">
                     <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center text-[#0066FF] group-hover:bg-[#0066FF] group-hover:text-white transition-colors">
                        <History size={20} />
                     </div>
                     <span className="font-bold text-base">이전 여행 기록</span>
                  </div>
                  <ChevronRight size={20} className="text-gray-300 group-hover:text-[#0066FF] group-hover:translate-x-1 transition-all" />
               </button>

               <button className="flex items-center justify-between p-6 bg-white border border-gray-100 text-gray-800 rounded-3xl transition-all group shadow-sm hover:shadow-md hover:border-red-100 active:scale-[0.98]">
                  <div className="flex items-center gap-4">
                     <div className="w-12 h-12 bg-red-50 rounded-2xl flex items-center justify-center text-red-500 group-hover:bg-red-500 group-hover:text-white transition-colors">
                        <Bookmark size={20} />
                     </div>
                     <span className="font-bold text-base">찜한 코스</span>
                  </div>
                  <ChevronRight size={20} className="text-gray-300 group-hover:text-red-500 group-hover:translate-x-1 transition-all" />
               </button>
            </div>
         </section>

         {/* Mascot Decor */}
         <div className="fixed bottom-24 right-4 pointer-events-none opacity-20 filter grayscale z-0">
            <img src="/mascot_circle.png" className="w-32 h-32 object-contain" alt="Decor" />
         </div>
      </div>
   );
};
