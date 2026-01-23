
"use client";

import React, { useState, useEffect } from 'react';
import { History, Bookmark, Settings, ChevronRight, Sparkles, TrendingUp, User } from 'lucide-react';
import { GeminiService } from '../services/geminiService';
import { SavedCourse } from '../types';

const aiService = new GeminiService();

/**
 * [Prompt 7: My Page Screen Refinement]
 */
export const MyPage = () => {
   const [savedCourses, setSavedCourses] = useState<SavedCourse[]>([]);

   useEffect(() => {
      aiService.getCourses().then(setSavedCourses);
   }, []);

   return (
      <div className="min-h-screen bg-white pb-40 overflow-y-auto font-['Inter'] hide-scrollbar">
         {/* Profile Header per Prompt 7 */}
         <header className="pt-24 px-10 pb-16 flex flex-col items-center bg-gradient-to-b from-blue-50/50 to-white rounded-b-[4rem]">
            <div className="relative mb-10">
               <div className="w-32 h-32 rounded-full overflow-hidden shadow-2xl ring-8 ring-white">
                  <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=400" className="w-full h-full object-cover" alt="Profile" />
               </div>
               <div className="absolute -bottom-1 -right-1 bg-[#0066FF] w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-blue-200 border-4 border-white">
                  <Sparkles size={20} />
               </div>
            </div>

            <div className="text-center mb-10">
               <h2 className="text-3xl font-black text-gray-900 tracking-tighter mb-2 italic uppercase">여행자님</h2>
               <div className="flex items-center gap-2 bg-white px-5 py-2 rounded-2xl border border-gray-100 shadow-sm">
                  <TrendingUp size={14} className="text-[#0066FF]" />
                  <p className="text-[11px] font-black text-gray-400 uppercase tracking-widest">나의 여행 횟수: <span className="text-[#0066FF]">3회</span></p>
               </div>
            </div>

            {/* Taste Keyword cluster per Prompt 7 */}
            <div className="flex gap-2.5 flex-wrap justify-center max-w-[300px]">
               {['#힐링', '#로컬맛집', '#빈티지', '#사진공유', '#도보여행'].map(tag => (
                  <span key={tag} className="bg-white px-5 py-2.5 rounded-2xl border border-gray-100 text-[11px] font-black text-gray-500 shadow-sm hover:shadow-md transition-all cursor-default">
                     {tag}
                  </span>
               ))}
            </div>
         </header>

         {/* Menu Section per Prompt 7 */}
         <section className="px-10 py-12 space-y-6">
            <h3 className="text-sm font-black text-gray-300 uppercase tracking-[0.3em] mb-4">Account Menu</h3>
            <div className="grid grid-cols-1 gap-4">
               <button className="flex items-center justify-between p-8 bg-gray-50/50 hover:bg-white border border-transparent hover:border-blue-100 text-gray-900 rounded-[2.5rem] transition-all group shadow-sm hover:shadow-xl">
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

            {/* AI Archived Courses */}
            <div className="pt-12 space-y-6">
               <div className="flex items-center justify-between px-2">
                  <h3 className="font-black text-lg text-gray-900 tracking-tighter italic">AI ARCHIVES</h3>
                  <TrendingUp size={18} className="text-green-500" />
               </div>

               {savedCourses.length === 0 ? (
                  <div className="p-16 text-center bg-gray-50 rounded-[3rem] border-2 border-dashed border-gray-100">
                     <p className="text-[10px] font-black text-gray-300 uppercase tracking-widest leading-relaxed">준비된 리포트가 없습니다<br />AI 가이드와 대화를 시작하세요</p>
                  </div>
               ) : (
                  <div className="space-y-4">
                     {savedCourses.map(course => (
                        <div key={course.id} className="bg-white border border-gray-100 p-8 rounded-[2.5rem] shadow-premium hover:shadow-2xl transition-all border-l-4 border-l-[#0066FF] animate-fade-in group">
                           <div className="flex justify-between items-start mb-4">
                              <span className="text-[10px] font-black text-gray-300">{course.createdAt.split('T')[0]}</span>
                              <ChevronRight size={16} className="text-gray-200" />
                           </div>
                           <h4 className="font-black text-gray-800 text-lg tracking-tight mb-2">{course.title}</h4>
                           <p className="text-xs font-bold text-gray-400 leading-relaxed line-clamp-2 mb-6">{course.description}</p>
                           <div className="pt-4 border-t border-gray-50 flex justify-between items-center">
                              <span className="text-[#0066FF] font-black text-sm italic">{course.totalBudget}</span>
                              <div className="flex -space-x-2">
                                 {[1, 2, 3].map(i => <div key={i} className="w-6 h-6 rounded-full border-2 border-white bg-gray-100" />)}
                              </div>
                           </div>
                        </div>
                     ))}
                  </div>
               )}
            </div>
         </section>
      </div>
   );
};
