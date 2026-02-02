"use client";

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Plus, X, ChevronDown, Mic, Utensils, Coffee, Music, MapPin, Bed } from 'lucide-react';
import { CoursePoint } from '../types';
import { InvitationPopup } from '../features/experience/InvitationPopup';

export const SurveyScreen = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [showInvitation, setShowInvitation] = useState(false);

  useEffect(() => {
    // 이미 거절하고 돌아온 경우(?reason=decline_invitation)에는 띄우지 않음
    if (searchParams.get('reason') !== 'decline_invitation') {
      setShowInvitation(true);
    }
  }, [searchParams]);

  const [courses, setCourses] = useState<CoursePoint[]>([
    { id: '1', type: '식당', name: '1. ' },
    { id: '2', type: '카페', name: '2. ' },
  ]);
  const [activeSelect, setActiveSelect] = useState<string | null>(null);
  const [budget, setBudget] = useState([10, 30]); // 5 ~ 50 range
  const [selectedThemes, setSelectedThemes] = useState(['데이트', '맛집탐방']);
  const [selectedCompanions, setSelectedCompanions] = useState(['연인']);
  const [selectedRegion, setSelectedRegion] = useState<string>('수완지구');
  const [customRegion, setCustomRegion] = useState('');
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [coords, setCoords] = useState<{ lat: number, lng: number } | null>(null);

  const themes = ['데이트', '힐링', '액티비티', '맛집탐방'];
  const companions = ['혼자', '친구', '연인', '가족'];
  const regions = ['수완지구', '충장로', '첨단지구', '상무지구', '내 중심', '기타'];

  const categories = [
    { type: '식당', icon: Utensils },
    { type: '카페', icon: Coffee },
    { type: '놀거리', icon: MapPin },
    { type: '숙박', icon: Bed },
  ] as const;

  const handleAdd = () => {
    if (courses.length >= 8) return;
    const nextIdx = courses.length + 1;
    setCourses([...courses, { id: Date.now().toString(), type: '식당', name: `${nextIdx}. ` }]);
  };

  const handleRemove = (id: string) => setCourses(courses.filter(c => c.id !== id));

  const updateType = (id: string, type: string) => {
    setCourses(courses.map(c => c.id === id ? { ...c, type: type as any } : c));
    setActiveSelect(null);
  };

  const handleRegionClick = (region: string) => {
    if (region === '내 중심') {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
            setSelectedRegion('내 중심');
            setIsCustomMode(false);
            alert("내 위치가 설정되었습니다.");
          },
          (err) => {
            alert("위치 정보를 가져올 수 없습니다. GPS 권한을 확인해주세요.");
          }
        );
      }
    } else if (region === '기타') {
      setIsCustomMode(true);
      setSelectedRegion('기타');
    } else {
      setIsCustomMode(false);
      setSelectedRegion(region);
      setCoords(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] pb-44 overflow-y-auto font-['Inter'] hide-scrollbar relative">
      <InvitationPopup isOpen={showInvitation} onClose={() => setShowInvitation(false)} />

      {/* Header - Soft Style */}
      <header className="bg-white/80 backdrop-blur-md px-6 py-4 flex items-center justify-center sticky top-0 z-[100] border-b border-gray-100">
        <h1 className="text-lg font-bold text-gray-800">여행 취향 분석</h1>
      </header>

      <div className="p-6 space-y-8 animate-fade-in transition-all">
        {/* Welcome Message - Soft Style */}
        <div className="flex gap-4 items-start">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shrink-0 shadow-md border border-orange-50 p-1 relative">
            <img src="/mascot_circle.png" className="w-full h-full object-cover scale-110" alt="mascot" />
          </div>
          <div className="flex-1 bg-white p-5 rounded-[2rem] rounded-tl-none shadow-sm border border-gray-100 relative">
            <p className="text-sm font-medium text-gray-600 leading-relaxed">
              <span className="font-bold text-gray-900 block mb-1">안녕하세요! 👋</span>
              어떤 여행을 꿈꾸시나요? 키워드를 선택해주시면 딱 맞는 코스를 추천해드릴게요.
            </p>
          </div>
        </div>

        {/* Main Survey Card - Warm Style */}
        <div className="space-y-10">

          {/* Region Selection */}
          <section className="space-y-4">
            <h3 className="font-bold text-gray-900 text-lg px-1">어디로 떠날까요?</h3>
            <div className="grid grid-cols-3 gap-2">
              {regions.map(r => (
                <button
                  key={r}
                  onClick={() => handleRegionClick(r)}
                  className={`py-3.5 rounded-2xl text-sm font-bold transition-all border ${selectedRegion === r
                      ? 'bg-white border-[#0066FF] text-[#0066FF] shadow-md shadow-blue-50'
                      : 'bg-white border-transparent text-gray-400 hover:bg-gray-50'
                    }`}
                >
                  {r}
                </button>
              ))}
            </div>
            {isCustomMode && (
              <input
                type="text"
                placeholder="직접 입력해주세요 (예: 동명동)"
                value={customRegion}
                onChange={(e) => setCustomRegion(e.target.value)}
                className="w-full p-4 mt-2 bg-white border border-gray-200 rounded-2xl font-bold text-gray-800 outline-none focus:border-[#0066FF] focus:ring-4 focus:ring-blue-50/50 transition-all placeholder:text-gray-300 placeholder:font-normal"
              />
            )}
            {coords && selectedRegion === '내 중심' && (
              <p className="text-[11px] text-[#0066FF] font-medium px-2 flex items-center gap-1">
                📍 현재 위치(GPS)를 확보했습니다.
              </p>
            )}
          </section>

          <section className="space-y-6">
            <div className="flex justify-between items-end px-1">
              <h3 className="font-bold text-gray-900 text-lg leading-none">원하는 코스 구성</h3>
              <span className="text-gray-400 font-medium text-xs bg-white px-2 py-1 rounded-full border border-gray-100">{courses.length} / 8</span>
            </div>

            <div className="space-y-4">
              {courses.map((c, i) => (
                <div key={c.id} className="relative space-y-3 animate-fade-in" style={{ animationDelay: `${i * 0.05}s` }}>
                  <div className="flex justify-between items-center px-1">
                    <span className="text-xs font-bold text-gray-400">{i + 1}번째 장소</span>
                    {courses.length > 1 && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRemove(c.id); }}
                        className="text-gray-300 hover:text-red-400 transition-colors p-1"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-4 gap-2">
                    {categories.map((cat) => (
                      <button
                        key={cat.type}
                        onClick={() => updateType(c.id, cat.type)}
                        className={`flex flex-col items-center gap-2 py-4 rounded-2xl border transition-all duration-200 ${c.type === cat.type
                            ? 'bg-white border-[#0066FF] text-[#0066FF] shadow-md shadow-blue-50'
                            : 'bg-white border-transparent text-gray-300 hover:bg-gray-50'
                          }`}
                      >
                        <cat.icon size={20} className={c.type === cat.type ? "stroke-2" : "stroke-1.5"} />
                        <span className="text-[11px] font-bold">{cat.type}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              <button
                onClick={handleAdd}
                className="w-full py-4 bg-white text-gray-400 rounded-2xl font-bold text-sm hover:text-[#0066FF] hover:border-blue-100 transition-all flex items-center justify-center gap-2 border border-dashed border-gray-200 mt-4 active:scale-[0.98]"
              >
                <Plus size={16} />
                장소 추가하기
              </button>
            </div>
          </section>

          {/* Theme Chips */}
          <section className="space-y-4">
            <h3 className="font-bold text-gray-900 text-lg px-1">여행 테마</h3>
            <div className="flex flex-wrap gap-2 text-wrap">
              {themes.map(t => (
                <button
                  key={t}
                  onClick={() => setSelectedThemes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t])}
                  className={`px-5 py-2.5 rounded-full text-sm font-bold transition-all border ${selectedThemes.includes(t)
                      ? 'bg-white border-[#0066FF] text-[#0066FF] shadow-md shadow-blue-50'
                      : 'bg-white border-transparent text-gray-400 hover:bg-gray-50'
                    }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </section>

          {/* Companion Chips */}
          <section className="space-y-4">
            <h3 className="font-bold text-gray-900 text-lg px-1">누구와 함께하나요?</h3>
            <div className="flex flex-wrap gap-2">
              {companions.map(c => (
                <button
                  key={c}
                  onClick={() => setSelectedCompanions([c])}
                  className={`px-5 py-2.5 rounded-full text-sm font-bold transition-all border ${selectedCompanions.includes(c)
                      ? 'bg-white border-[#0066FF] text-[#0066FF] shadow-md shadow-blue-50'
                      : 'bg-white border-transparent text-gray-400 hover:bg-gray-50'
                    }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </section>

          {/* Budget Range slider */}
          <section className="space-y-8 p-6 bg-white rounded-3xl border border-gray-100 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-blue-50 rounded-bl-full opacity-50 pointer-events-none" />
            <div className="flex justify-between items-center relative z-10">
              <h3 className="font-bold text-gray-900 text-lg">예산 범위</h3>
              <p className="text-[#0066FF] font-black text-lg bg-blue-50 px-3 py-1 rounded-lg">{budget[0]} ~ {budget[1]} <span className="text-sm font-medium text-gray-500">만원</span></p>
            </div>

            <div className="px-2 relative h-10 flex items-center mt-4">
              {/* Dual Range Track */}
              <div className="absolute inset-0 mx-2 h-2 bg-gray-100 rounded-full top-[16px]">
                <div
                  className="absolute h-full bg-[#0066FF] rounded-full opacity-80"
                  style={{
                    left: `${((budget[0] - 5) / 45) * 100}%`,
                    right: `${100 - ((budget[1] - 5) / 45) * 100}%`
                  }}
                />
              </div>
              {/* Invisible Range Inputs */}
              <input
                type="range"
                min="5"
                max="50"
                step="1"
                value={budget[0]}
                onChange={(e) => {
                  const val = Math.min(parseInt(e.target.value), budget[1] - 1);
                  setBudget([val, budget[1]]);
                }}
                className="absolute w-full h-10 appearance-none bg-transparent pointer-events-none z-30 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-8 [&::-webkit-slider-thumb]:h-8 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-transparent [&::-webkit-slider-thumb]:cursor-pointer"
              />
              <input
                type="range"
                min="5"
                max="50"
                step="1"
                value={budget[1]}
                onChange={(e) => {
                  const val = Math.max(parseInt(e.target.value), budget[0] + 1);
                  setBudget([budget[0], val]);
                }}
                className="absolute w-full h-10 appearance-none bg-transparent pointer-events-none z-30 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-8 [&::-webkit-slider-thumb]:h-8 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-transparent [&::-webkit-slider-thumb]:cursor-pointer"
              />
              {/* Visual Handles */}
              <div
                className="absolute w-7 h-7 bg-white border-[3px] border-[#0066FF] rounded-full shadow-lg pointer-events-none transition-transform active:scale-125"
                style={{ left: `calc(${((budget[0] - 5) / 45) * 100}% - 14px + 8px)` }}
              />
              <div
                className="absolute w-7 h-7 bg-white border-[3px] border-[#0066FF] rounded-full shadow-lg pointer-events-none transition-transform active:scale-125"
                style={{ left: `calc(${((budget[1] - 5) / 45) * 100}% - 14px + 8px)` }}
              />
            </div>
            <div className="flex justify-between items-center px-1 text-[11px] font-bold text-gray-300 mt-1">
              <span>최소 5만원</span>
              <span>최대 50만원</span>
            </div>
          </section>

          <div className="flex flex-col gap-3 pt-4">
            <button
              onClick={async () => {
                const userId = localStorage.getItem('temp_user_id');
                const regionStr = selectedRegion === '기타' ? customRegion : (selectedRegion === '내 중심' && coords ? `${coords.lat},${coords.lng}` : selectedRegion);

                if (userId) {
                  try {
                    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
                    await fetch(`${apiUrl}/user/survey`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        userId,
                        region: regionStr,
                        courses,
                        themes: selectedThemes,
                        companions: selectedCompanions,
                        budget,
                        has_specific_place: "N" // 초기값
                      })
                    });
                  } catch (e) {
                    console.error("Survey sync failed", e);
                  }
                }
                // 코스 생성 중 UI를 보여주기 위해 파라미터 전달
                router.push('/chat?mode=course_init');
              }}
              className="w-full py-5 bg-[#0066FF] text-white rounded-full font-bold text-lg shadow-xl shadow-blue-200 active:scale-[0.98] transition-all flex items-center justify-center gap-2 hover:bg-[#0052cc]"
            >
              <span className="text-xl">✨</span> 맞춤 코스 만들기
            </button>
            <button
              onClick={() => router.push('/chat')}
              className="w-full py-4 text-gray-400 font-medium text-sm hover:text-gray-600 transition-all underline decoration-gray-200 underline-offset-4"
            >
              건너뛰고 채팅으로 대화하기
            </button>
          </div>
        </div>
      </div>

      {/* Input Simulator at Bottom (Image 1) */}
      <div className="fixed bottom-24 left-6 right-6 z-[200] animate-slide-up">
        <div className="bg-white/90 backdrop-blur-md border border-gray-200 rounded-2xl p-4 flex items-center gap-4 shadow-2xl">
          <Mic size={24} className="text-gray-400" />
          <input
            type="text"
            placeholder="프롬프트를 입력하세요..."
            className="flex-1 bg-transparent border-none outline-none font-medium text-gray-700 placeholder:text-gray-300"
            readOnly
            onClick={() => router.push('/chat')}
          />
        </div>
      </div>
    </div>
  );
};
