"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Star, ArrowRight, ArrowLeft, Heart, Zap, Map, LayoutList } from 'lucide-react';

export const TastingNoteScreen = () => {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [tripPlaces, setTripPlaces] = React.useState<any[]>([]);
    const [answers, setAnswers] = useState({
        satisfaction: 0,
        atmosphere: '',
        movement: '',
        bestPlace: '',
        cardChoice: ''
    });

    React.useEffect(() => {
        const stored = localStorage.getItem('current_course');
        if (stored) {
            setTripPlaces(JSON.parse(stored));
        }
    }, []);

    const nextStep = () => {
        if (step < 5) setStep(prev => prev + 1);
        else handleFinish();
    };

    const prevStep = () => {
        if (step > 1) setStep(prev => prev - 1);
    };

    const handleFinish = async () => {
        const userId = localStorage.getItem('temp_user_id');
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
            await fetch(`${API_URL}/user/session/tasting-notes?user_id=${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    satisfaction: answers.satisfaction,
                    atmosphere: answers.atmosphere === 'good' ? 5 : 3, // Mapping string to int for simple demo
                    movement: answers.movement === 'good' ? 5 : 3,
                    best_place: answers.bestPlace,
                    card_choice_style: answers.cardChoice
                })
            });
        } catch (e) {
            console.error("Failed to save tasting notes", e);
        }
        router.push('/home');
    };

    const questions = [
        {
            id: 1,
            title: "오늘의 여행은 만족스러우셨나요?",
            subtitle: "별점으로 당신의 기분을 알려주세요.",
            icon: Star,
            component: (
                <div className="flex justify-center gap-3">
                    {[1, 2, 3, 4, 5].map(star => (
                        <motion.button
                            key={star}
                            whileTap={{ scale: 0.8 }}
                            onClick={() => { setAnswers({ ...answers, satisfaction: star }); nextStep(); }}
                            className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${answers.satisfaction >= star ? 'bg-[#0066FF] text-white shadow-lg' : 'bg-gray-100 text-gray-300'}`}
                        >
                            <Star size={28} fill={answers.satisfaction >= star ? "currentColor" : "none"} />
                        </motion.button>
                    ))}
                </div>
            )
        },
        {
            id: 2,
            title: "전체적인 분위기는 어땠나요?",
            subtitle: "AI 에이전트의 스타일을 학습합니다.",
            icon: Heart,
            options: [
                { label: "감성적이고 조용한", value: "moody" },
                { label: "활기차고 복작거리는", value: "active" },
                { label: "전통적이고 고즈넉한", value: "classic" }
            ],
            field: 'atmosphere'
        },
        {
            id: 3,
            title: "이동 동선은 편리했나요?",
            subtitle: "Tmap 경로 최적화를 위한 피드백입니다.",
            icon: Map,
            options: [
                { label: "매우 효율적이었어요", value: "efficient" },
                { label: "조금 멀었지만 괜찮았어요", value: "ok" },
                { label: "동선이 꼬여서 힘들었어요", value: "bad" }
            ],
            field: 'movement'
        },
        {
            id: 4,
            title: "오늘의 '최애' 장소는 어디인가요?",
            subtitle: "가장 만족스러웠던 장소 하나를 선택해주세요.",
            icon: Zap,
            component: (
                <div className="grid grid-cols-2 gap-4">
                    {tripPlaces.map((place) => (
                        <motion.button
                            key={place.id}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => {
                                setAnswers({ ...answers, bestPlace: place.name });
                                nextStep();
                            }}
                            className={`relative aspect-[4/5] rounded-3xl overflow-hidden border-4 transition-all ${answers.bestPlace === place.name ? 'border-[#0066FF] shadow-lg' : 'border-transparent'
                                }`}
                        >
                            <img src={place.img} className="w-full h-full object-cover" alt={place.name} />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                            <div className="absolute bottom-4 left-4 right-4 text-left">
                                <p className="text-white font-black text-sm leading-tight">{place.name}</p>
                            </div>
                        </motion.button>
                    ))}
                </div>
            )
        },
        {
            id: 5,
            title: "AI 큐레이션 품질은 어떠셨나요?",
            subtitle: "더 정확한 추천을 위해 취향을 학습합니다.",
            icon: LayoutList,
            options: [
                { label: "완벽하게 제 스타일이었어요", value: "perfect" },
                { label: "보통이었어요", value: "normal" },
                { label: "조금 더 개선이 필요해요", value: "need_work" }
            ],
            field: 'cardChoice'
        }
    ];

    const currentQ = questions[step - 1];

    return (
        <div className="min-h-screen bg-white flex flex-col font-['Inter']">
            {/* Progress Bar */}
            <div className="fixed top-0 left-0 right-0 h-1.5 bg-gray-50 z-50">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(step / 5) * 100}%` }}
                    className="h-full bg-[#0066FF]"
                />
            </div>

            {/* Header */}
            <header className="p-6 flex items-center justify-between">
                <button onClick={prevStep} className={`p-1 text-gray-300 ${step === 1 ? 'opacity-0' : ''}`}>
                    <ArrowLeft size={24} />
                </button>
                <span className="text-xs font-black text-blue-400 tracking-tighter uppercase">Travel Tasting Note</span>
                <div className="w-8" />
            </header>

            {/* Question Content */}
            <main className="flex-1 px-8 pt-12 pb-20 flex flex-col">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={step}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className="space-y-10"
                    >
                        <div className="space-y-3">
                            <div className="w-16 h-16 bg-blue-50 rounded-[2rem] flex items-center justify-center text-[#0066FF] mb-6 shadow-sm">
                                <currentQ.icon size={32} />
                            </div>
                            <h1 className="text-3xl font-black text-gray-900 leading-tight">
                                {currentQ.title}
                            </h1>
                            <p className="text-gray-400 font-medium font-sm">
                                {currentQ.subtitle}
                            </p>
                        </div>

                        <div className="space-y-3">
                            {currentQ.options ? (
                                currentQ.options.map((opt) => (
                                    <button
                                        key={opt.value}
                                        onClick={() => {
                                            //@ts-ignore
                                            setAnswers({ ...answers, [currentQ.field]: opt.value });
                                            nextStep();
                                        }}
                                        className={`w-full p-5 text-left rounded-3xl font-bold border-2 transition-all active:scale-[0.98] ${
                                            //@ts-ignore
                                            answers[currentQ.field] === opt.value
                                                ? 'bg-blue-50 border-[#0066FF] text-[#0066FF]'
                                                : 'bg-white border-gray-50 text-gray-400 hover:border-blue-100 hover:text-gray-600'
                                            }`}
                                    >
                                        {opt.label}
                                    </button>
                                ))
                            ) : (
                                currentQ.component
                            )}
                        </div>
                    </motion.div>
                </AnimatePresence>
            </main>

            {/* Footer Navigation */}
            <div className="p-8">
                <button
                    onClick={nextStep}
                    disabled={step === 1 && answers.satisfaction === 0}
                    className="w-full py-6 bg-gray-900 text-white rounded-3xl font-black text-xl shadow-2xl flex items-center justify-center gap-3 active:scale-[0.98] disabled:opacity-30 transition-all"
                >
                    {step === 5 ? '테이스팅 노트 완성하기' : '다음 단계로'}
                    <ArrowRight size={22} />
                </button>
            </div>
        </div>
    );
};
