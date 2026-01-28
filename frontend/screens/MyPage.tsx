
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
      <div className="min-h-screen bg-white pb-40 overflow-y-auto font-['Inter'] hide-scrollbar relative">
         {/* Top Navigation / Logout */}
         <button
            onClick={handleLogout}
            className="absolute top-8 right-8 z-10 flex items-center gap-2 px-4 py-2.5 bg-white/80 backdrop-blur-md border border-gray-100 rounded-full text-gray-400 hover:text-red-500 hover:bg-red-50 hover:border-red-100 transition-all shadow-sm active:scale-95 group"
            aria-label="로그아웃"
         >
            <LogOut size={16} className="group-hover:stroke-red-500 transition-colors" />
            <span className="text-xs font-black tracking-tight">로그아웃</span>
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
            <div className="flex gap-2.5 flex-wrap justify-center max-w-[300px]">
               {['#힐링', '#로컬맛집', '#빈티지', '#사진공유', '#도보여행'].map((tag, i) => (
                  <span key={i} className="bg-white px-5 py-2.5 rounded-2xl border border-gray-100 text-sm font-black text-gray-500 shadow-sm hover:shadow-md transition-all cursor-default animate-fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
                     {tag}
                  </span>
               ))}
            </div>
         </header>

         {/* Menu Section per Prompt 7 */}
         <section className="px-10 py-12 space-y-6">
            <h3 className="text-sm font-black text-gray-300 uppercase tracking-[0.3em] mb-4">Account Menu</h3>
            <div className="grid grid-cols-1 gap-4">
               <button
                  onClick={() => router.push('/history')}
                  className="flex items-center justify-between p-8 bg-gray-50/50 hover:bg-white border border-transparent hover:border-blue-100 text-gray-900 rounded-[2.5rem] transition-all group shadow-sm hover:shadow-xl">
                  <div className="flex items-center gap-5 font-black text-base tracking-tight">
                     <div className="p-4 bg-white rounded-2xl shadow-sm text-blue-500 group-hover:bg-[#0066FF] group-hover:text-white transition-all"><History size={22} /></div>
                     이전 여행 기록
                  </div>
                  <ChevronRight size={20} className="text-gray-300 group-hover:translate-x-1 transition-transform" />
               </button>

               <button className="flex items-center justify-between p-8 bg-gray-50/50 hover:bg-white border border-transparent hover:border-red-100 text-gray-900 rounded-[2.5rem] transition-all group shadow-sm hover:shadow-xl">
                  <div className="flex items-center gap-5 font-black text-base tracking-tight">
                     <div className="p-4 bg-white rounded-2xl shadow-sm text-red-500 group-hover:bg-red-500 group-hover:text-white transition-all"><Bookmark size={22} /></div>
                     찜한 코스
                  </div>
                  <ChevronRight size={20} className="text-gray-300 group-hover:translate-x-1 transition-transform" />
               </button>


            </div>
         </section>
      </div>
   );
};
