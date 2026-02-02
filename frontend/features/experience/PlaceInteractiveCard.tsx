"use client";

import React, { useState } from 'react';
import { RefreshCw, CheckCircle2, Info, MapPin, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Place {
    id: string;
    name: string;
    description: string;
    imageUrl: string;
    category: string;
    lat: number;
    lng: number;
}

interface Props {
    places: Place[];
    currentIndex: number;
    onPick: (place: Place) => void;
    onSkip: () => void;
    onFinish: () => void;
}

export const PlaceInteractiveCard = ({ places, currentIndex, onPick, onSkip, onFinish }: Props) => {
    const currentPlace = places[currentIndex];

    const handlePick = (e: React.MouseEvent) => {
        e.stopPropagation();
        onPick(currentPlace);
    };

    const handleSkip = (e: React.MouseEvent) => {
        e.stopPropagation();
        onSkip();
    };

    if (!currentPlace) return null;

    return (
        <div className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm flex items-center justify-center px-6 font-['Inter'] overflow-hidden">
            <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                className="bg-white w-full max-w-[480px] rounded-[2.5rem] overflow-hidden shadow-2xl flex flex-col max-h-[70vh] relative"
            >
                {/* 상단 이미지 영역 - vh 기준 높이 제한 */}
                <div className="w-full h-[30vh] relative shrink-0">
                    <motion.img
                        key={currentPlace.id}
                        initial={{ opacity: 0, scale: 1.1 }}
                        animate={{ opacity: 1, scale: 1 }}
                        src={currentPlace.imageUrl}
                        alt={currentPlace.name}
                        className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

                    {/* 진행률 바 */}
                    <div className="absolute top-6 left-6 right-6 flex gap-1">
                        {places.map((_, idx) => (
                            <div key={idx} className="flex-1 h-1 bg-white/20 rounded-full overflow-hidden">
                                <motion.div
                                    initial={false}
                                    animate={{ width: idx <= currentIndex ? '100%' : '0%' }}
                                    className={`h-full ${idx === currentIndex ? 'bg-white' : 'bg-white/40'}`}
                                />
                            </div>
                        ))}
                    </div>

                    <div className="absolute bottom-4 left-6 right-6 text-left">
                        <span className="bg-blue-500 text-white text-[9px] font-black px-2.5 py-1 rounded-md uppercase tracking-wider mb-2 inline-block">
                            {currentPlace.category}
                        </span>
                        <h3 className="text-white text-xl font-black tracking-tight">{currentPlace.name}</h3>
                    </div>
                </div>

                {/* 정보 및 액션 구역 */}
                <div className="flex-1 w-full bg-white p-6 pb-32 flex flex-col justify-between overflow-y-auto custom-scrollbar">
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 text-blue-500">
                            <MapPin size={14} />
                            <span className="text-[9px] font-black uppercase tracking-widest text-left">Spot Insight</span>
                        </div>
                        <p className="text-gray-500 text-xs leading-relaxed font-medium text-left">
                            {currentPlace.description}
                        </p>
                    </div>

                    {/* 하단 액션 버튼 - pb-32로 인해 네비게이션 바 위로 올라감 */}
                    <div className="pt-6 flex flex-col gap-2">
                        <button
                            onClick={handlePick}
                            className="w-full py-4 bg-[#0066FF] text-white rounded-2xl font-black text-base flex items-center justify-center gap-2 shadow-lg shadow-blue-100 active:scale-[0.98] transition-all"
                        >
                            <CheckCircle2 size={20} /> 이 장소 담기
                        </button>
                        <button
                            onClick={handleSkip}
                            className="w-full py-2 text-gray-400 font-bold text-xs flex items-center justify-center gap-1 hover:text-gray-600 transition-colors"
                        >
                            <RefreshCw size={14} /> 다른 장소 물색
                        </button>
                    </div>
                </div>

                {/* 닫기 버튼 (옵션: discovery 종료용) */}
                <button
                    onClick={onFinish}
                    className="absolute top-4 right-4 z-20 p-2 bg-black/40 hover:bg-black/60 rounded-full text-white transition-colors"
                >
                    <X size={16} />
                </button>
            </motion.div>
        </div>
    );
};
