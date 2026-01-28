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
        <div className="min-h-screen bg-white font-['Inter']">
            {/* Header */}
            <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-md px-6 py-4 flex items-center justify-between border-b border-gray-100">
                <button
                    onClick={() => router.back()}
                    className="p-2 -ml-2 hover:bg-gray-50 rounded-full transition-colors"
                >
                    <ChevronLeft size={24} className="text-gray-900" />
                </button>
                <h1 className="text-lg font-black text-gray-900 tracking-tight">이전 여행 기록</h1>
                <div className="w-10" /> {/* Spacer */}
            </div>

            {/* Content */}
            <div className="p-6 space-y-6 pb-20">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4" />
                        <p className="text-xs">기록을 불러오는 중...</p>
                    </div>
                ) : courses.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                        <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mb-4 text-gray-300">
                            <Calendar size={32} />
                        </div>
                        <p className="text-gray-500 font-bold mb-1">저장된 여행 코스가 없습니다</p>
                        <p className="text-xs text-gray-400">AI와 대화하여 새로운 추억을 만들어보세요!</p>
                    </div>
                ) : (
                    courses.map((course) => (
                        <div
                            key={course.id}
                            onClick={() => handleCourseClick(course)}
                            className="bg-white border border-gray-100 rounded-[2rem] p-6 shadow-premium hover:shadow-xl hover:scale-[1.02] transition-all cursor-pointer group active:scale-[0.98]"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex items-center gap-2 text-xs font-bold text-blue-500 bg-blue-50 px-3 py-1 rounded-full">
                                    <Clock size={12} />
                                    {course.createdAt.split('T')[0]}
                                </div>
                                <div className="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center group-hover:bg-blue-500 group-hover:text-white transition-colors">
                                    <ChevronRight size={16} />
                                </div>
                            </div>

                            <h3 className="text-xl font-black text-gray-900 mb-2 leading-tight group-hover:text-blue-600 transition-colors">
                                {course.title}
                            </h3>
                            <p className="text-sm text-gray-500 line-clamp-2 mb-6 leading-relaxed">
                                {course.description}
                            </p>

                            <div className="flex items-center gap-4 pt-4 border-t border-gray-50 text-xs font-bold text-gray-400">
                                <div className="flex items-center gap-1.5">
                                    <MapPin size={14} />
                                    {course.points.length}개 장소
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <DollarSign size={14} />
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
