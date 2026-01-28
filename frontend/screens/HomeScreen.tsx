
"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, MapPin, Calendar, Clock } from 'lucide-react';

export const HomeScreen = () => {
    const router = useRouter();

    return (
        <div className="min-h-screen bg-[#F8FAFC] pb-32 font-['Inter'] hide-scrollbar">
            {/* Hero Section */}
            <section className="bg-[#0066FF] pt-20 pb-16 px-8 rounded-b-[4rem] shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl" />
                <div className="relative z-10">
                    <p className="text-blue-100 font-bold text-sm mb-2 opacity-80 uppercase tracking-widest">Travel with AI</p>
                    <h1 className="text-4xl font-black text-white leading-tight italic tracking-tighter">
                        광주에서의<br />
                        특별한 하루를<br />
                        설계해 보세요.
                    </h1>
                </div>
            </section>

            <div className="p-8 space-y-10 animate-fade-in">
                {/* Quick Action */}
                <div
                    onClick={() => router.push('/survey')}
                    className="bg-white p-8 rounded-[2.5rem] shadow-premium border border-gray-100 flex items-center justify-between group cursor-pointer active:scale-95 transition-all"
                >
                    <div>
                        <h3 className="text-xl font-black text-gray-900 mb-1">새 코스 만들기</h3>
                        <p className="text-sm font-bold text-gray-400">당신만의 맞춤 일정을 생성합니다.</p>
                    </div>
                    <div className="w-14 h-14 bg-blue-50 text-[#0066FF] rounded-2xl flex items-center justify-center group-hover:bg-[#0066FF] group-hover:text-white transition-all">
                        <Sparkles size={28} />
                    </div>
                </div>

                {/* Info Cards - Real data integration needed */}
                {/* 
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-50">
                        <div className="w-10 h-10 bg-orange-50 text-orange-500 rounded-xl flex items-center justify-center mb-4">
                            <MapPin size={20} />
                        </div>
                        <h4 className="font-black text-gray-800 text-sm mb-1">추천 장소</h4>
                        <p className="text-[10px] font-bold text-gray-400">실시간 핫플레이스</p>
                    </div>
                    <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-50">
                        <div className="w-10 h-10 bg-green-50 text-green-500 rounded-xl flex items-center justify-center mb-4">
                            <Calendar size={20} />
                        </div>
                        <h4 className="font-black text-gray-800 text-sm mb-1">내 일정</h4>
                        <p className="text-[10px] font-bold text-gray-400">관리 중인 코스 0개</p>
                    </div>
                </div> 
                */}
            </div>
        </div>
    );
};
