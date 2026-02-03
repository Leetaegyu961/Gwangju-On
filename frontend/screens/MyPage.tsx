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
               <button className="w-full flex items-center justify-between p-5 bg-white hover:bg-blue-50/50 border border-transparent hover:border-blue-100 text-gray-800 rounded-3xl transition-all group shadow-sm hover:shadow-md">
                  <div className="flex items-center gap-4 font-bold text-sm">
                     <div className="p-3 bg-gray-50 rounded-2xl text-gray-600 group-hover:bg-[#3B82F6] group-hover:text-white transition-all">
                        <Bookmark size={20} />
                     </div>
                     찜한 코스
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
