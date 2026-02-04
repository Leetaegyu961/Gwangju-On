"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { X, Sparkles, ChevronRight, Loader2, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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

    // 기본 데이터 (AI 에이전트 신호 부재 시 폴백용)
    const defaultInvitation = {
        id: 'course-1',
        title: "예술과 역사를 모두 만나는 광주 여행",
        description: "송정골에서 즐기는 정통 굴비정식부터 이이남 스튜디오의 미디어아트까지, 광주의 혼을 느껴보세요.",
        imageUrl: "https://placehold.co/800x450/0066FF/FFFFFF/png?text=Gwangju+On"
    };

    const data = invitationData || defaultInvitation;
    const [imageError, setImageError] = useState(false);

    const handleAccept = async () => {
        setIsLoading(true);

        // 1. 맥락 유지: 초대장 수락 여부를 로컬 스토리지에 저장 (Discovery에서 테마 선택 유도용)
        localStorage.setItem('invitation_accepted', 'true');

        // 2. 리다이렉트 (게스트도 Discovery 접근 허용)
        router.push('/discovery');
    };

    const handleCloseInternal = () => {
        onClose();
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

        // (doNotShowToday 로직 제거됨)

        router.push('/survey?reason=decline_invitation');
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[1000] flex items-center justify-center px-6">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={handleCloseInternal}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white w-full max-w-[480px] rounded-[2.5rem] overflow-hidden shadow-2xl relative z-10 flex flex-col max-h-[85vh]"
                    >
                        {/* 닫기 버튼 */}
                        <button
                            onClick={handleCloseInternal}
                            className="absolute top-4 right-4 z-20 p-2 bg-black/40 hover:bg-black/60 rounded-full text-white transition-colors"
                        >
                            <X size={18} />
                        </button>

                        {/* 상단 이미지 영역 - vh 기준 높이 제한 */}
                        <div className="w-full aspect-video relative overflow-hidden shrink-0">
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
                        <div className="p-6 pb-24 space-y-6 text-left overflow-y-auto custom-scrollbar">
                            <p className="text-gray-500 text-sm leading-relaxed font-medium">
                                {data.description}
                            </p>

                            <div className="flex flex-col gap-3">
                                <button
                                    onClick={handleAccept}
                                    disabled={isLoading}
                                    className="w-full py-4 bg-[#0066FF] text-white rounded-2xl font-black text-base shadow-lg shadow-blue-100 flex items-center justify-center gap-2 active:scale-[0.98] transition-all disabled:opacity-70"
                                >
                                    {isLoading ? (
                                        <Loader2 className="animate-spin" size={20} />
                                    ) : (
                                        <>이 여행으로 시작하기 <ChevronRight size={18} /></>
                                    )}
                                </button>

                                <button
                                    onClick={handleDecline}
                                    className="w-full py-2 text-gray-400 font-bold text-sm hover:text-gray-600 transition-colors"
                                >
                                    다른 제안이 좋아요
                                </button>

                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};
