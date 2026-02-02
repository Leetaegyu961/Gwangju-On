
"use client";

import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { User, ChevronRight, Sparkles } from 'lucide-react';

export const ProfileSetupScreen = () => {
    const router = useRouter();
    const searchParams = useSearchParams();
    const mode = searchParams.get('mode') || 'guest';
    const [gender, setGender] = useState<'male' | 'female' | null>(null);
    const [age, setAge] = useState<string | null>(null);

    const ages = ['20대 이하', '20대', '30대', '40대', '50대 이상'];

    const handleComplete = async () => {
        if (gender && age) {
            try {
                // 1. 백엔드로 데이터 전송
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
                const response = await fetch(`${apiUrl}/user/onboard`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ gender, age }),
                });

                if (response.ok) {
                    const data = await response.json();

                    // 2. 받은 임시 ID(userId)를 브라우저에 저장
                    localStorage.setItem('temp_user_id', data.userId);
                    console.log('Server Onboarding Success:', data);

                    // 3. 다음 화면으로 이동
                    router.push('/survey');
                } else {
                    console.error('Server Error');
                    // 에러가 나도 일단 데모 진행을 위해 넘어갈지 결정 (여기선 일단 넘어감)
                    router.push('/survey');
                }
            } catch (error) {
                console.error('Network Error:', error);
                router.push('/survey');
            }
        }
    };

    const handleGenderSelect = (selected: 'male' | 'female') => {
        setGender(selected);
    };

    const handleAgeSelect = (selected: string) => {
        setAge(selected);
    };

    return (
        <div className="min-h-screen bg-[#FDFBF7] flex flex-col p-6 font-['Inter'] relative overflow-hidden">
            {/* Background Decoration */}
            <div className="absolute top-[-10%] right-[-20%] w-96 h-96 bg-blue-50/50 rounded-full blur-3xl opacity-60 pointer-events-none" />

            {/* Header */}
            <div className="mt-8 mb-10 relative z-10 animate-fade-in">
                <div className="w-16 h-16 bg-white rounded-full shadow-md shadow-blue-50 mb-4 flex items-center justify-center overflow-hidden border border-blue-50 relative">
                    <img src="/mascot_circle.png" className="w-full h-full object-cover scale-110" alt="Mascot" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 leading-snug">
                    더 정확한 추천을 위해<br />
                    <span className="text-[#0066FF]">기본 정보</span>를 알려주세요
                </h1>
                <p className="text-gray-400 text-sm mt-2">입력하신 정보는 여행 코스 추천에만 사용됩니다.</p>
            </div>

            <div className="space-y-10 relative z-10">
                {/* Gender Selection */}
                <section className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                    <h3 className="text-sm font-bold text-gray-600 mb-4 px-1">성별</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <button
                            onClick={() => handleGenderSelect('male')}
                            className={`relative py-5 rounded-2xl transition-all border-2 flex flex-col items-center justify-center gap-2 group ${gender === 'male'
                                ? 'bg-white border-[#0066FF] shadow-lg shadow-blue-100'
                                : 'bg-white border-transparent hover:border-blue-100 shadow-sm'
                                }`}
                        >
                            <span className={`text-2xl transition-transform group-active:scale-90 ${gender === 'male' ? 'scale-110' : 'grayscale opacity-50'}`}>🙋‍♂️</span>
                            <span className={`text-sm font-bold ${gender === 'male' ? 'text-[#0066FF]' : 'text-gray-400'}`}>남성</span>
                            {gender === 'male' && <div className="absolute top-3 right-3 w-2 h-2 rounded-full bg-[#0066FF]" />}
                        </button>
                        <button
                            onClick={() => handleGenderSelect('female')}
                            className={`relative py-5 rounded-2xl transition-all border-2 flex flex-col items-center justify-center gap-2 group ${gender === 'female'
                                ? 'bg-white border-[#0066FF] shadow-lg shadow-blue-100'
                                : 'bg-white border-transparent hover:border-blue-100 shadow-sm'
                                }`}
                        >
                            <span className={`text-2xl transition-transform group-active:scale-90 ${gender === 'female' ? 'scale-110' : 'grayscale opacity-50'}`}>🙋‍♀️</span>
                            <span className={`text-sm font-bold ${gender === 'female' ? 'text-[#0066FF]' : 'text-gray-400'}`}>여성</span>
                            {gender === 'female' && <div className="absolute top-3 right-3 w-2 h-2 rounded-full bg-[#0066FF]" />}
                        </button>
                    </div>
                </section>

                {/* Age Selection */}
                <section className="animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
                    <div className="flex justify-between items-end mb-4 px-1">
                        <h3 className="text-sm font-bold text-gray-600">연령대</h3>
                        {age && <span className="text-xs text-[#0066FF] font-medium animate-fade-in">{age} 선택됨</span>}
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        {ages.map((a) => (
                            <button
                                key={a}
                                onClick={() => handleAgeSelect(a)}
                                className={`py-3.5 rounded-xl font-medium text-sm transition-all border ${age === a
                                    ? 'bg-[#0066FF] text-white border-[#0066FF] shadow-md shadow-blue-200'
                                    : 'bg-white text-gray-500 border-gray-100 hover:bg-gray-50 hover:border-gray-200'
                                    }`}
                            >
                                {a}
                            </button>
                        ))}
                    </div>
                </section>
            </div>

            <div className="mt-auto pt-10 pb-6 relative z-10 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
                <button
                    onClick={handleComplete}
                    disabled={!gender || !age}
                    className={`w-full py-4 rounded-full font-bold text-base transition-all flex items-center justify-center gap-2 shadow-lg ${gender && age
                        ? 'bg-[#0066FF] text-white shadow-blue-200 hover:bg-[#0052cc] active:scale-[0.98]'
                        : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                        }`}
                >
                    다음으로
                    <ChevronRight size={18} />
                </button>
            </div>
        </div>
    );
};