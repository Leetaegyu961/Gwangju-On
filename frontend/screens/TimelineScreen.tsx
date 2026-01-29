"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Camera, Calendar, MapPin, ChevronDown, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function TimelineScreen() {
    const router = useRouter();
    const [course, setCourse] = useState<any[]>([]);
    const [photos, setPhotos] = useState<{ [key: number]: string }>({});

    useEffect(() => {
        // 저장된 코스 불러오기
        const stored = localStorage.getItem('current_course');
        if (stored) {
            setCourse(JSON.parse(stored));
        }

        // 이전에 업로드한 사진이 있다면 불러오기 (임시)
        // 실제로는 DB나 별도 스토리지에 저장 필요
    }, []);

    const handleImageUpload = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setPhotos(prev => ({
                    ...prev,
                    [index]: reader.result as string
                }));
            };
            reader.readAsDataURL(file);
        }
    };

    const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\./g, '.');

    if (course.length === 0) {
        return (
            <div className="h-screen bg-[#FDFBF7] flex flex-col items-center justify-center p-6 text-center font-['Inter']">
                <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm border border-orange-100">
                    <Calendar size={32} className="text-orange-300" />
                </div>
                <h2 className="text-xl font-black text-gray-800 mb-3">아직 여행 기록이 없어요</h2>
                <p className="text-gray-500 mb-8 text-sm leading-relaxed">
                    AI 가이드에게 코스를 추천받고<br />
                    나만의 여행 앨범을 시작해보세요!
                </p>
                <button
                    onClick={() => router.push('/chat')}
                    className="px-8 py-3.5 bg-[#FF6B00] text-white font-bold rounded-full shadow-lg shadow-orange-200 active:scale-95 transition-all text-sm"
                >
                    여행 코스 추천받기
                </button>
            </div>
        );
    }

    // 기본 이미지 (사진 없을 때)
    const placeholders = [
        "/placeholder-1.jpg", // 실제로는 적절한 기본 이미지 URL 필요
        "/placeholder-2.jpg",
        "/placeholder-3.jpg"
    ];

    return (
        <div className="min-h-screen bg-[#FDFBF7] font-['Inter'] relative pb-32">
            {/* 배경 텍스처 효과 (CSS로 은은한 종이 질감 연출) */}
            <div className="fixed inset-0 opacity-[0.03] pointer-events-none z-0"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")` }}
            />

            {/* 1. 앨범 커버 (Album Cover) */}
            <section className="relative px-6 pt-12 pb-16 z-10 flex flex-col items-center">
                {/* 날짜 및 제목 */}
                <div className="text-center mb-10 animate-fade-in-up">
                    <h1 className="text-3xl font-black text-gray-900 mb-3 tracking-tight">광주에서 보낸 오후.</h1>
                    <div className="flex items-center justify-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
                        <span>#혼행</span>
                        <span>#힐링</span>
                        <span>•</span>
                        <span>{today}</span>
                        <span>•</span>
                        <span>광주 동구</span>
                    </div>
                </div>

                {/* 폴라로이드 콜라주 */}
                <div className="relative w-full max-w-[320px] aspect-[4/5] mx-auto mb-6">

                    {/* 사진 3: 오른쪽 아래 (가장 뒤) */}
                    {course.length > 2 && (
                        <div className="absolute top-[45%] right-0 w-[55%] aspect-[3/4] bg-white p-2 pb-8 shadow-lg transform rotate-[6deg] rounded-sm transition-all duration-700 hover:rotate-[8deg] hover:z-20 cursor-pointer border border-gray-100/50">
                            <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                <img src={photos[2] || course[2].img || placeholders[2]} className="w-full h-full object-cover filter sepia-[0.1]" alt="photo3" />
                                {!photos[2] && <div className="absolute inset-0 flex items-center justify-center bg-black/5"><Camera className="text-white/50" /></div>}
                            </div>
                        </div>
                    )}

                    {/* 사진 2: 왼쪽 아래 (중간) */}
                    {course.length > 1 && (
                        <div className="absolute top-[40%] left-0 w-[55%] aspect-[3/4] bg-white p-2 pb-8 shadow-lg transform rotate-[-5deg] rounded-sm transition-all duration-700 hover:rotate-[-7deg] hover:z-20 cursor-pointer border border-gray-100/50">
                            <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                <img src={photos[1] || course[1].img || placeholders[1]} className="w-full h-full object-cover filter sepia-[0.1]" alt="photo2" />
                                {!photos[1] && <div className="absolute inset-0 flex items-center justify-center bg-black/5"><Camera className="text-white/50" /></div>}
                            </div>
                        </div>
                    )}

                    {/* 사진 1: 메인 (가장 앞) */}
                    {course.length > 0 && (
                        <div className="absolute top-0 left-[15%] w-[70%] aspect-[3/4] bg-white p-3 pb-10 shadow-2xl transform rotate-[2deg] rounded-sm z-10 transition-all duration-700 hover:scale-105 cursor-pointer border border-gray-100/50">
                            <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                <img src={photos[0] || course[0].img || placeholders[0]} className="w-full h-full object-cover filter contrast-[1.05]" alt="photo1" />
                                {!photos[0] && <div className="absolute inset-0 flex items-center justify-center bg-black/5"><Camera className="text-white/50" size={32} /></div>}
                            </div>
                        </div>
                    )}
                </div>

                {/* 하단 찢어진 종이 데코 및 위치 표시 */}
                <div className="relative w-full max-w-[280px] bg-white/60 backdrop-blur-sm py-3 px-6 text-center transform rotate-[-1deg] shadow-sm animate-fade-in-up delay-200">
                    {/* 찢어진 효과 (CSS mask/clip-path로 흉내낼 수 있으나 여기선 간단히 점선으로 대체) */}
                    <div className="absolute top-0 left-0 right-0 h-[2px] bg-transparent border-t-2 border-dashed border-gray-300"></div>
                    <div className="flex items-center justify-center gap-2 text-gray-600 font-bold text-sm">
                        <MapPin size={16} className="text-[#FF6B00]" />
                        <span>{today} • 광주 동구</span>
                    </div>
                    <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-transparent border-b-2 border-dashed border-gray-300"></div>
                </div>
            </section>

            {/* 2. 내지 (상세 코스 & 업로드) */}
            <section className="px-6 pb-20 z-10 relative">
                <div className="flex items-center gap-4 mb-8">
                    <div className="h-[1px] bg-gray-200 flex-1"></div>
                    <span className="text-xs font-bold text-gray-400">MEMORY LOG</span>
                    <div className="h-[1px] bg-gray-200 flex-1"></div>
                </div>

                <div className="space-y-12 relative">
                    {/* 타임라인 세로선 */}
                    <div className="absolute left-[19px] top-4 bottom-4 w-[2px] bg-gray-200 -z-10 bg-repeat-y" style={{ backgroundImage: 'linear-gradient(to bottom, #E5E7EB 50%, transparent 50%)', backgroundSize: '2px 10px' }}></div>

                    {course.map((spot, index) => (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            key={index}
                            className="flex gap-5"
                        >
                            {/* 왼쪽: 순서 마커 */}
                            <div className="shrink-0 relative">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center z-10 shadow-sm border-4 border-[#FDFBF7] ${photos[index] ? 'bg-[#FF6B00] text-white' : 'bg-white text-gray-400'}`}>
                                    {photos[index] ? <CheckCircle2 size={18} /> : <span className="text-sm font-black">{index + 1}</span>}
                                </div>
                            </div>

                            {/* 오른쪽: 카드 */}
                            <div className="flex-1 bg-white p-5 rounded-2xl shadow-sm border border-gray-100/50">
                                <div className="mb-4">
                                    <h3 className="text-lg font-black text-gray-800">{spot.name}</h3>
                                    <p className="text-xs text-gray-400 mt-1">{spot.desc || "잠시 쉬기 좋은 공간"}</p>
                                </div>

                                {/* 사진 업로드 영역 */}
                                <label className="block w-full aspect-[4/3] bg-gray-50 rounded-xl overflow-hidden relative cursor-pointer group transition-all hover:shadow-md border border-gray-100">
                                    <input
                                        type="file"
                                        accept="image/*"
                                        className="hidden"
                                        onChange={(e) => handleImageUpload(index, e)}
                                    />
                                    {photos[index] ? (
                                        <img src={photos[index]} alt="uploaded" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                                    ) : (
                                        <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-300 group-hover:text-[#FF6B00] transition-colors">
                                            <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center shadow-sm mb-2 group-hover:scale-110 transition-transform">
                                                <Camera size={24} />
                                            </div>
                                            <span className="text-xs font-bold">사진 남기기</span>
                                        </div>
                                    )}
                                    {/* 사진 수정 오버레이 (이미 있을 때) */}
                                    {photos[index] && (
                                        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                            <span className="bg-white/90 px-3 py-1.5 rounded-full text-xs font-bold text-gray-700 shadow-sm">수정하기</span>
                                        </div>
                                    )}
                                </label>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* 하단 메시지 */}
            <div className="px-6 pb-12 text-center">
                <p className="text-sm text-gray-400 font-medium">
                    모든 장소의 사진을 채워<br />나만의 지도를 완성해보세요 🎨
                </p>
            </div>

        </div>
    );
}
