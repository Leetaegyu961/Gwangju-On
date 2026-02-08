import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, MapPin, X, ArrowRight, Check } from 'lucide-react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { EffectCards } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/effect-cards';
import { CourseInfo } from '../../types';

interface InvitationModalProps {
    isOpen: boolean;
    onClose: () => void;
    // invitationCourses: CourseInfo[]; // 나중에 API로 받아올 타입
    invitationCourses: any[];
    onApply: (course: any) => void;
}

const InvitationModal: React.FC<InvitationModalProps> = ({ isOpen, onClose, invitationCourses, onApply }) => {
    const router = useRouter();

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80 backdrop-blur-md animate-fade-in">
            <div className="w-full max-w-lg p-6 relative">
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-white/50 hover:text-white transition-colors p-2 rounded-full hover:bg-white/10 z-10"
                >
                    <X size={24} />
                </button>

                {/* Header */}
                <div className="text-center text-white mb-8">
                    <div className="inline-flex items-center gap-2 bg-white/20 px-4 py-1.5 rounded-full backdrop-blur-sm mb-4 border border-white/10">
                        <Sparkles size={14} className="text-yellow-300" />
                        <span className="text-xs font-bold tracking-widest uppercase">Special Invitation</span>
                    </div>
                    <h2 className="text-3xl font-black mb-2 leading-tight">
                        여행자님을 위한<br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-purple-300">
                            3가지 맞춤 코스
                        </span>가 도착했어요
                    </h2>
                    <p className="text-white/60 text-sm">
                        지난 여행 취향을 분석해 큐레이션 했습니다.<br />
                        마음에 드는 여정을 선택해 보세요.
                    </p>
                </div>

                {/* Card Slider */}
                <div className="mb-10">
                    <Swiper
                        effect={'cards'}
                        grabCursor={true}
                        modules={[EffectCards]}
                        className="mySwiper w-[320px] h-[420px]"
                    >
                        {invitationCourses.map((course, idx) => (
                            <SwiperSlide key={course.course_id || idx} className="bg-white rounded-[2rem] p-6 shadow-2xl flex flex-col relative overflow-hidden">
                                {/* Badge */}
                                <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-blue-500 to-purple-500" />

                                <div className="mt-2 mb-4">
                                    <span className="text-xs font-black text-blue-500 uppercase tracking-widest bg-blue-50 px-3 py-1 rounded-lg">
                                        THEME 0{idx + 1}
                                    </span>
                                    <h3 className="text-2xl font-black text-gray-900 mt-2 line-clamp-2">
                                        {course.title}
                                    </h3>
                                    <p className="text-gray-500 text-sm mt-1 line-clamp-2">
                                        {course.description}
                                    </p>
                                </div>

                                {/* Places Preview */}
                                <div className="flex-1 space-y-3 overflow-y-auto hide-scrollbar">
                                    {course.places.slice(0, 4).map((place: any, pIdx: number) => (
                                        <div key={pIdx} className="flex items-start gap-3 p-3 bg-gray-50 rounded-xl">
                                            <div className="w-10 h-10 rounded-lg bg-gray-200 flex-shrink-0 overflow-hidden">
                                                {place.img ? (
                                                    <img src={place.img} className="w-full h-full object-cover" alt={place.name} />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                                                        <MapPin size={16} />
                                                    </div>
                                                )}
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-gray-900 text-sm">{place.name}</h4>
                                                <p className="text-xs text-gray-500 line-clamp-1">{place.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* Apply Button */}
                                <button
                                    onClick={() => onApply(course)}
                                    className="mt-4 w-full bg-black text-white py-4 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-gray-800 transition-colors shadow-lg active:scale-95"
                                >
                                    <Check size={18} />
                                    이 코스로 바로 시작
                                </button>
                            </SwiperSlide>
                        ))}
                    </Swiper>
                </div>

                {/* Footer Actions */}
                <div className="text-center">
                    <button
                        onClick={onClose}
                        className="text-white/60 text-sm font-medium hover:text-white transition-colors underline decoration-transparent hover:decoration-white/60 underline-offset-4"
                    >
                        괜찮아요, 직접 설문할래요 (나가기)
                    </button>
                </div>
            </div>
        </div>
    );
};

export default InvitationModal;
