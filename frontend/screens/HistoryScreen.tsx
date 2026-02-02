"use client";

import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Calendar, MapPin, DollarSign, Clock } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { GeminiService } from '../services/geminiService';
import { SavedCourse } from '../types';

const aiService = new GeminiService();

export const HistoryScreen = () => {
    const router = useRouter();
    const [courses, setCourses] = useState<SavedCourse[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        aiService.getCourses().then(data => {
            setCourses(data);
            setLoading(false);
        });
    }, []);

    const handleCourseClick = (course: SavedCourse) => {
        // 선택한 코스를 로컬 스토리지 'current_course'에 저장하여 MapView에서 로드할 수 있게 함
        // 필요한 형태: { id, name, lat, lng, desc, tags, transport, img }[]
        // SavedCourse.points 구조가 이미 거의 일치함 (type 필드 제외하면)

        const mapPoints = course.points.map(p => ({
            id: p.id,
            name: p.name,
            lat: p.lat || 0,
            lng: p.lng || 0,
            desc: p.reason || p.desc || '', // desc or reason fallback
            tags: p.tags || [],
            transport: p.transport || '이동',
            img: p.img || p.imageUrl || '' // img or imageUrl fallback
        }));

        localStorage.setItem('current_course', JSON.stringify(mapPoints));
        router.push('/map');
    };

    return (
        <div className="min-h-screen bg-[#FDFBF7] font-['Inter']">
            {/* Header */}
            <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md px-6 py-4 flex items-center justify-between border-b border-gray-100">
                <button
                    onClick={() => router.back()}
                    className="p-2 -ml-2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                    <ChevronLeft size={24} />
                </button>
                <h1 className="text-lg font-bold text-gray-800">이전 여행 기록</h1>
                <div className="w-10" />
            </header>

            {/* Content */}
            <div className="p-6 space-y-5 pb-20">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-32 text-gray-400 gap-4">
                        <div className="w-12 h-12 border-4 border-blue-100 border-t-[#0066FF] rounded-full animate-spin" />
                        <p className="text-sm font-medium animate-pulse">추억을 불러오는 중...</p>
                    </div>
                ) : courses.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in-up">
                        <div className="w-48 h-48 mb-6 relative">
                            <div className="absolute inset-0 bg-orange-100 rounded-full blur-2xl opacity-50 animate-pulse" />
                            <img src="/mascot_full.png" alt="Empty" className="w-full h-full object-contain relative z-10 drop-shadow-lg grayscale-[20%]" />
                        </div>
                        <h2 className="text-xl font-bold text-gray-800 mb-3">아직 다녀온 여행이 없어요!</h2>
                        <p className="text-sm text-gray-500 mb-8 max-w-[240px] leading-relaxed font-medium">
                            AI 큐레이터와 함께<br />광주에서의 첫 번째 추억을 만들어보세요.
                        </p>
                        <button
                            onClick={() => router.push('/chat')}
                            className="px-8 py-3.5 bg-[#0066FF] text-white rounded-full font-bold shadow-lg shadow-blue-200 hover:bg-[#0052cc] transition-all active:scale-95 flex items-center gap-2 group"
                        >
                            <span>지금 여행 시작하기</span>
                            <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>
                ) : (
                    courses.map((course) => (
                        <div
                            key={course.id}
                            onClick={() => handleCourseClick(course)}
                            className="bg-white border border-gray-100 rounded-[2rem] p-6 shadow-sm hover:shadow-lg hover:border-blue-100 hover:scale-[1.01] transition-all cursor-pointer group active:scale-[0.98] animate-fade-in"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex items-center gap-2 text-xs font-bold text-[#0066FF] bg-blue-50 px-3 py-1.5 rounded-full">
                                    <Clock size={12} />
                                    {course.createdAt.split('T')[0]}
                                </div>
                                <div className="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center group-hover:bg-[#0066FF] group-hover:text-white transition-all shadow-sm">
                                    <ChevronRight size={16} />
                                </div>
                            </div>

                            <h3 className="text-lg font-bold text-gray-800 mb-2 leading-tight group-hover:text-[#0066FF] transition-colors line-clamp-1">
                                {course.title}
                            </h3>
                            <p className="text-sm text-gray-500 line-clamp-2 mb-6 leading-relaxed">
                                {course.description}
                            </p>

                            <div className="flex items-center gap-4 pt-4 border-t border-gray-50 text-xs font-bold text-gray-500">
                                <div className="flex items-center gap-1.5">
                                    <MapPin size={14} className="text-gray-400" />
                                    {course.points.length}개 스팟
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <DollarSign size={14} className="text-gray-400" />
                                    {course.totalBudget}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
