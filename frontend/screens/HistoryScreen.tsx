"use client";

import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Calendar, MapPin, DollarSign, Clock, Trash2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { GeminiService } from '../services/geminiService';
import { SavedCourse } from '../types';

const aiService = new GeminiService();

export const HistoryScreen = () => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const mode = searchParams.get('mode'); // 'confirmed' or null

    const [courses, setCourses] = useState<SavedCourse[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // [Sync] 사용자 정보 동기화 후 목록 로드
        aiService.syncUser().then(() => {
            aiService.getCourses().then(data => {
                console.log('📊 [HistoryScreen] 전체 코스 데이터:', data);
                console.log('📊 [HistoryScreen] 현재 모드:', mode);

                let filtered = [];
                if (mode === 'confirmed') {
                    // [Filter] 확정된 코스 모두 표시
                    filtered = data.filter(c => {
                        console.log(`코스 "${c.title}":`, {
                            is_selected: c.is_selected,
                            timeline_generated: c.timeline_generated,
                            포함여부: c.is_selected
                        });
                        return c.is_selected;
                    });
                } else {
                    // [Filter] 후보 코스만 (히스토리)
                    filtered = data.filter(c => !c.is_selected);
                }

                console.log('✅ [HistoryScreen] 필터링된 코스:', filtered);
                setCourses(filtered);
                setLoading(false);
            });
        });
    }, [mode]);

    const handleDeleteCourse = async (courseId: string, e: React.MouseEvent) => {
        e.stopPropagation();

        if (mode === 'confirmed') {
            // 확정한 코스에서 제거 (타임라인에는 남음)
            if (!confirm("이 코스를 확정 목록에서 제거하시겠습니까?\n(타임라인 앨범은 유지됩니다)")) return;
        } else {
            // 히스토리에서 완전 삭제
            if (!confirm("정말 이 여행 기록을 삭제하시겠습니까? (복구 불가)")) return;
        }

        const userId = localStorage.getItem('temp_user_id');
        if (!userId) return;

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

            let res;
            if (mode === 'confirmed') {
                // 확정한 코스에서만 제거 (is_selected = false)
                res = await fetch(`${API_URL.replace(/\/api\/?$/, '')}/api/journey/${courseId}/unselect`, {
                    method: 'PATCH'
                });
            } else {
                // 완전 삭제
                res = await fetch(`${API_URL.replace(/\/api\/?$/, '')}/api/journey/${courseId}?userId=${userId}`, {
                    method: 'DELETE'
                });
            }

            if (res.ok) {
                setCourses(prev => prev.filter(c => c.id !== courseId));
                alert(mode === 'confirmed' ? '확정 목록에서 제거되었습니다.' : '삭제되었습니다.');
            } else {
                alert('삭제 실패');
            }
        } catch (error) {
            console.error('Failed to delete course', error);
            alert('삭제 중 오류가 발생했습니다.');
        }
    };

    const handleCourseClick = (course: SavedCourse) => {
        // [Feature] Restore Full Recommendation Set
        // 같은 그룹(추천 세션)에 속한 코스들을 모두 찾아 지도에 복원합니다.
        let relatedCourses = [course];
        if (course.groupId) {
            // 같은 그룹 ID를 가진 코스들을 찾음 (현재 목록 내에서)
            const peers = courses.filter(c => c.groupId === course.groupId);
            if (peers.length > 0) {
                relatedCourses = peers;
            }
        }

        // MapView 호환 포맷으로 변환
        const mapCourses = relatedCourses.map(c => ({
            course_id: c.id,
            course_name: c.title,
            description: c.description,
            places: c.points || [],
            cards: [], // 저장된 카드 정보가 없으므로 빈 배열 (지도에서는 마커 위주로 표시됨)
            is_selected: c.is_selected !== undefined ? c.is_selected : true // [Mod] 확정 상태 전달
        }));

        // 클릭된 코스가 지도에서 선택된 상태로 시작하도록 설정
        const currentMeta = mapCourses.find(m => m.course_id === course.id) || mapCourses[0];

        // 3. LocalStorage 업데이트 -> MapView가 이를 읽어서 초기화
        localStorage.setItem('all_courses', JSON.stringify(mapCourses));
        localStorage.setItem('current_course', JSON.stringify(course.points || []));
        localStorage.setItem('current_course_meta', JSON.stringify(currentMeta));

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
                <h1 className="text-lg font-black text-gray-900 tracking-tight">
                    {mode === 'confirmed' ? '나의 확정 코스' : '추천 코스 히스토리'}
                </h1>
                <div className="w-10" />
            </div>

            {/* Content */}
            <div className="p-6 space-y-6 pb-20">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4" />
                        <p className="text-xs">기록을 불러오는 중...</p>
                    </div>
                ) : courses.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
                        <div className="w-40 h-40 mb-6 opacity-80 grayscale-[20%]">
                            <img src="/mascot_full.png" alt="Empty" className="w-full h-full object-contain" />
                        </div>
                        <p className="text-gray-900 font-black text-lg mb-2">아직 추천받은 코스가 없어요!</p>
                        <p className="text-gray-400 text-sm font-medium mb-8 leading-relaxed">
                            나만의 특별한 여행을<br />
                            AI에게 추천받아보세요.
                        </p>
                        <button
                            onClick={() => router.push('/chat')}
                            className="px-8 py-4 bg-[#0066FF] text-white rounded-full font-bold shadow-lg shadow-blue-200 active:scale-95 transition-all flex items-center gap-2"
                        >
                            여행 시작하기 <ChevronRight size={18} />
                        </button>
                    </div>
                ) : (
                    courses.map((course) => (
                        <div
                            key={course.id}
                            onClick={() => handleCourseClick(course)}
                            className="bg-white border border-gray-100 rounded-[2rem] p-6 shadow-sm hover:shadow-xl transition-all cursor-pointer group active:scale-[0.98] relative overflow-hidden"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex items-center gap-2 text-xs font-bold text-gray-500 bg-gray-50 px-3 py-1 rounded-full">
                                    <Clock size={12} />
                                    {(course.createdAt || new Date().toISOString()).split('T')[0]}
                                </div>
                                <button
                                    onClick={(e) => handleDeleteCourse(course.id, e)}
                                    className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-full transition-all z-20"
                                >
                                    <Trash2 size={14} />
                                </button>
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
                                    {course.totalBudget || '예산 산출 중'}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
