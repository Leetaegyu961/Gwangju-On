"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { X, Sparkles, ChevronRight, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import invitationCoursesData from '../../../data/invitation_courses.json';
import { getCourseImage } from '../../utils/courseImages';

// Fix for React 19 type mismatch
const MotionDiv = motion.div as any;
const MotionImg = motion.img as any;

interface InvitationPopupProps {
    isOpen: boolean;
    onClose: () => void;
    invitationData?: {
        id: string;
        title: string;
        description: string;
        imageUrl: string;
    };
}

export const InvitationPopup = ({ isOpen, onClose, invitationData }: InvitationPopupProps) => {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const [selectedInvitation, setSelectedInvitation] = useState<any>(null);

    const pickRandomCourse = () => {
        const randomIdx = Math.floor(Math.random() * invitationCoursesData.length);
        const course = invitationCoursesData[randomIdx];

        const randomImages = [
            "https://images.unsplash.com/photo-1534234828563-025816976a44?w=800&q=80", // 1. 고즈넉한 한옥/전통 (C1)
            "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800&q=80", // 2. 여행/가방/지도 (C2)
            "https://images.unsplash.com/photo-1596436889106-be35c843f974?w=800&q=80", // 3. 힐링/공원 (C3)
            "https://images.unsplash.com/photo-1566127444979-b3d2b654e3d7?w=800&q=80", // 4. 역사/건물 (C4)
            "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80", // 5. 도심/카페거리 (C5)
            "https://images.unsplash.com/photo-1627740924089-a29d89299403?w=800&q=80", // 6. 활기찬 거리 (C6)
            "https://images.unsplash.com/photo-1506161986422-48df74ce0076?w=800&q=80"  // 7. 등산/자연 (C7)
        ];

        const finalData = {
            id: course.id,
            title: course.title,
            description: course.description,
            imageUrl: randomImages[randomIdx] || "https://placehold.co/800x450/0066FF/FFFFFF/png?text=Gwangju+On",
            places: course.places.map((p: any, idx: number) => ({
                ...p,
                // invitation_courses.json의 img 필드를 imageUrl로 매핑
                imageUrl: p.img || p.imageUrl || getCourseImage([p.type || "여행"], p.name)
            }))
        };
        setSelectedInvitation(finalData);
    };

    // 랜덤 코스 선택 (클라이언트 사이드 마운트 후)
    React.useEffect(() => {
        if (!invitationData) {
            pickRandomCourse();
        } else {
            setSelectedInvitation(invitationData);
        }
    }, [invitationData]);

    const data = selectedInvitation || {
        id: 'loading',
        title: "여행 초대장을 읽는 중...",
        description: "잠시만 기다려주세요.",
        imageUrl: "https://placehold.co/800x450/f3f4f6/d1d5db/png?text=Loading..."
    };
    const [imageError, setImageError] = useState(false);

    const handleAccept = async () => {
        setIsLoading(true);

        // [MODIFIED] Discovery 단계 생략 -> 바로 지도(Map)로 이동하여 코스 표시
        const coursePlaces = data.places || [];
        const userId = typeof window !== 'undefined' ? localStorage.getItem('temp_user_id') : null;
        const hasAccessToken = typeof window !== 'undefined' ? !!localStorage.getItem('access_token') : false;

        // [Feature] Auto-Save Invitation to History (로그인 사용자만)
        if (userId && hasAccessToken) {
            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const response = await fetch(`${API_URL.replace(/\/api\/?$/, '')}/api/journey/save-final`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        userId: userId,
                        selectedCourseIndex: 0, // 초대장 코스는 항상 선택됨
                        customPlaces: null,
                        // Invitation Data -> CourseMeta 변환
                        allCourses: [{
                            course_id: null, // 새로운 코스이므로 null
                            course_name: data.title,
                            course_description: data.description,
                            places: coursePlaces
                        }],
                        aiSummary: "초대장으로 받은 특별한 여행 코스"
                    })
                });

                const result = await response.json();
                console.log("✅ Invitation saved to history:", result);
            } catch (e) {
                console.error("Failed to save invitation to history", e);
            }
        } else if (userId && !hasAccessToken) {
            // 게스트는 백엔드에 저장하지 않음
            console.log("ℹ️ Guest user - invitation not saved to backend");
        }

        // 1. localStorage 저장 (Map 호환용)
        localStorage.setItem('current_course', JSON.stringify(coursePlaces));

        // 단일 코스를 all_courses 배열(1개)로도 저장하여 UI 통일성 유지
        const singleCourseObj = [{
            course_id: 1,
            course_name: data.title,
            course_description: data.description,
            places: coursePlaces
        }];
        localStorage.setItem('all_courses', JSON.stringify(singleCourseObj));

        // pending_invitation은 더 이상 필요 없으므로 제거
        localStorage.removeItem('pending_invitation');

        // 3. 권한 확인 및 이동
        const hasTempUserId = !!localStorage.getItem('temp_user_id');

        // 게스트(temp_user_id만 있음) 또는 로그인 사용자 모두 지도로 이동
        if (hasAccessToken || hasTempUserId) {
            // 로그인 상태 또는 게스트: 바로 지도로 이동
            router.push('/map');
        } else {
            // 완전히 비로그인 상태: 로그인 후 지도로 이동
            router.push('/login?redirect=/map&mode=accept_invitation');
        }
    };

    const handleDecline = async () => {
        // 사일런트 데이터 로깅 (반려 이력 기록)
        try {
            const userId = localStorage.getItem('access_token') || localStorage.getItem('temp_user_id') || 'guest';
            await fetch('http://localhost:8000/api/journey/log-action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userId,
                    actionType: 'REJECT_INVITATION',
                    data: { invitationId: data.id }
                })
            });
        } catch (e) {
            console.error("Silent logging failed", e);
        }

        // [MODIFIED] 거절 시 팝업 닫기
        onClose();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[1000] flex items-center justify-center px-6">
                    <MotionDiv
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                    />
                    <MotionDiv
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white w-full max-w-[480px] rounded-[2.5rem] overflow-hidden shadow-2xl relative z-10 flex flex-col max-h-[85vh]"
                    >
                        {/* 닫기 버튼 */}
                        <button
                            onClick={onClose}
                            className="absolute top-4 right-4 z-20 p-2 bg-black/40 hover:bg-black/60 rounded-full text-white transition-colors"
                        >
                            <X size={18} />
                        </button>

                        {/* 상단 이미지 영역 - vh 기준 높이 제한 */}
                        <div className="w-full h-40 relative overflow-hidden shrink-0">
                            <img
                                src={imageError ? "https://placehold.co/800x450/0066FF/FFFFFF/png?text=Gwangju+On" : data.imageUrl}
                                onError={() => setImageError(true)}
                                alt={data.title}
                                className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                            <div className="absolute bottom-4 left-6 right-6 text-left">
                                <div className="flex items-center gap-2 mb-1">
                                    <Sparkles className="text-yellow-400" size={12} />
                                    <span className="text-white/90 text-[10px] font-black tracking-widest uppercase">Special Invitation</span>
                                </div>
                                <h2 className="text-white text-lg font-black leading-tight">
                                    {data.title}
                                </h2>
                            </div>
                        </div>

                        {/* 상세 설명 및 액션 버튼 - 스크롤 가능 구역 */}
                        {/* 상세 설명 및 액션 버튼 - 스크롤 가능 구역 */}
                        <div className="p-6 pb-32 space-y-6 text-left overflow-y-auto custom-scrollbar flex-1">
                            <p className="text-gray-500 text-sm leading-relaxed font-medium">
                                {data.description}
                            </p>

                            {/* [ADD] 장소 리스트 미리보기 */}
                            <div className="space-y-3">
                                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                                    <span className="w-1 h-1 bg-gray-400 rounded-full"></span>
                                    포함된 장소 ({data.places?.length || 0})
                                </h3>
                                <div className="grid grid-cols-1 gap-2">
                                    {data.places?.slice(0, 5).map((place: any, idx: number) => (
                                        <div key={idx} className="flex items-center gap-3 p-2.5 rounded-xl bg-gray-50 border border-gray-100 hover:bg-blue-50 transition-colors">
                                            <div className="w-10 h-10 rounded-lg overflow-hidden shrink-0 bg-gray-200 border border-gray-200">
                                                <img
                                                    src={place.imageUrl || "https://placehold.co/100x100/e2e8f0/94a3b8?text=Place"}
                                                    className="w-full h-full object-cover"
                                                    alt={place.name}
                                                />
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <div className="text-xs font-black text-gray-800 truncate mb-0.5">{place.name}</div>
                                                <div className="text-[10px] text-gray-500 truncate font-medium">{place.type || '추천 장소'} · {place.desc || '함께 가기 좋은 곳'}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* 하단 고정 버튼 영역 */}
                        <div className="absolute bottom-0 left-0 right-0 p-6 bg-white border-t border-gray-50 flex gap-3 z-30">
                            <button
                                onClick={handleDecline}
                                className="flex-1 py-4 bg-gray-100 text-gray-500 rounded-2xl font-bold text-sm hover:bg-gray-200 transition-colors active:scale-95"
                            >
                                거절
                            </button>

                            <button
                                onClick={handleAccept}
                                disabled={isLoading}
                                className="flex-1 py-4 bg-[#0066FF] text-white rounded-2xl font-black text-sm shadow-lg shadow-blue-100 flex items-center justify-center gap-2 active:scale-95 transition-all disabled:opacity-70"
                            >
                                {isLoading ? (
                                    <Loader2 className="animate-spin" size={20} />
                                ) : (
                                    <>수락 <ChevronRight size={16} /></>
                                )}
                            </button>
                        </div>
                    </MotionDiv>
                </div>
            )}
        </AnimatePresence>
    );
};
