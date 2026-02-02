"use client";

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Menu, Plus, X, ChevronDown, Mic, Utensils, Coffee, Music, MapPin, Bed } from 'lucide-react';
import { CoursePoint } from '../types';
import { DiscoverySideModal } from '../components/DiscoverySideModal';
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
  const [isSideOpen, setIsSideOpen] = useState(false);
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
    <div className="min-h-screen bg-[#F8FAFC] pb-44 overflow-y-auto font-['Inter'] hide-scrollbar relative">
      <InvitationPopup isOpen={showInvitation} onClose={() => setShowInvitation(false)} />
      <DiscoverySideModal isOpen={isSideOpen} onClose={() => setIsSideOpen(false)} />

      {/* Header - Image 1 Style (Blue) */}
      <header className="bg-[#0066FF] px-6 py-5 flex items-center sticky top-0 z-[100] shadow-md">
        <button onClick={() => setIsSideOpen(true)} className="p-1 -ml-1 text-white">
          <Menu size={28} />
        </button>
        <h1 className="flex-1 text-center text-xl font-bold tracking-tight text-white pr-8">AI 여행 가이드</h1>
      </header>

      <div className="p-6 space-y-8 animate-fade-in transition-all">
        {/* Welcome Message - Image 1 Style (Bot + Blue Bubble) */}
        <div className="flex gap-4 items-start">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shrink-0 shadow-sm overflow-hidden border border-blue-100">
            <img src="https://cdni.iconscout.com/illustration/premium/thumb/robot-assistant-8631166-6872583.png" className="w-12 h-12 object-contain" alt="bot" />
          </div>
          <div className="flex-1 bg-[#1E6BFF] p-5 rounded-[2rem] rounded-tl-none shadow-lg relative">
            {/* Tail */}
            <div className="absolute top-0 -left-2 w-4 h-4 bg-[#1E6BFF] [clip-path:polygon(100%_0,0_0,100%_100%)]" />
            <p className="text-sm font-bold text-white leading-relaxed">
              안녕하세요! 어떤 여행을 원하시나요?<br />
              키워드를 선택해주세요.
            </p>
          </div>
        </div>

        {/* Main Survey Card - Image 1 Style */}
        <div className="bg-white rounded-[2.5rem] p-8 shadow-sm border border-gray-100 space-y-10">

          {/* Region Selection */}
          <section className="space-y-4">
            <h3 className="font-bold text-gray-900 text-lg">지역</h3>
            <div className="grid grid-cols-3 gap-2">
              {regions.map(r => (
                <button
                  key={r}
                  onClick={() => handleRegionClick(r)}
                  className={`py-3 rounded-xl text-sm font-bold transition-all border-2 ${selectedRegion === r ? 'bg-blue-50 border-[#0066FF] text-[#0066FF]' : 'bg-white border-gray-50 text-gray-400'}`}
                >
                  {r}
                </button>
              ))}
            </div>
            {isCustomMode && (
              <input
                type="text"
                placeholder="어디로 가고 싶으신가요?"
                value={customRegion}
                onChange={(e) => setCustomRegion(e.target.value)}
                className="w-full p-4 mt-2 bg-gray-50 border-none rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-100"
              />
            )}
            {coords && selectedRegion === '내 중심' && (
              <p className="text-[11px] text-[#0066FF] font-bold px-1">위도: {coords.lat.toFixed(4)}, 경도: {coords.lng.toFixed(4)} (GPS 획득 완료)</p>
            )}
          </section>

          <section className="space-y-6">
            <div className="flex justify-between items-end">
              <h3 className="font-bold text-gray-900 text-lg leading-none">장소 (코스 구성)</h3>
              <span className="text-gray-400 font-medium text-xs">{courses.length} / 8</span>
            </div>

            <div className="space-y-8">
              {courses.map((c, i) => (
                <div key={c.id} className="relative space-y-3 animate-fade-in" style={{ animationDelay: `${i * 0.05}s` }}>
                  <div className="flex justify-between items-center px-1">
                    <span className="text-xs font-black text-[#0066FF] uppercase tracking-wider">{i + 1}번째 방문지</span>
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
                        className={`flex flex-col items-center gap-2 py-4 rounded-2xl border-2 transition-all duration-200 ${c.type === cat.type
                          ? 'bg-blue-50 border-[#0066FF] text-[#0066FF] shadow-sm shadow-blue-100 scale-[1.02]'
                          : 'bg-white border-gray-50 text-gray-300 hover:border-gray-200 hover:text-gray-500'
                          }`}
                      >
                        <cat.icon size={20} />
                        <span className="text-[11px] font-bold">{cat.type}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              <button
                onClick={handleAdd}
                className="w-full py-4 bg-[#F0F7FF] text-[#0066FF] rounded-2xl font-bold text-base hover:bg-blue-100 transition-all flex items-center justify-center gap-2 border-2 border-dashed border-blue-200"
              >
                <Plus size={18} />
                코스 추가하기
              </button>
            </div>
          </section>

          {/* Theme Chips */}
          <section className="space-y-4">
            <h3 className="font-bold text-gray-900 text-lg">테마</h3>
            <div className="flex flex-wrap gap-2 text-wrap">
              {themes.map(t => (
                <button
                  key={t}
                  onClick={() => setSelectedThemes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t])}
                  className={`px-6 py-2.5 rounded-full text-sm font-bold transition-all ${selectedThemes.includes(t) ? 'bg-[#0066FF] text-white' : 'bg-gray-100 text-gray-400'}`}
                >
                  {t}
                </button>
              ))}
            </div>
          </section>

          {/* Companion Chips */}
          <section className="space-y-4">
            <h3 className="font-bold text-gray-900 text-lg">동행인</h3>
            <div className="flex flex-wrap gap-2">
              {companions.map(c => (
                <button
                  key={c}
                  onClick={() => setSelectedCompanions([c])}
                  className={`px-6 py-2.5 rounded-full text-sm font-bold transition-all ${selectedCompanions.includes(c) ? 'bg-[#0066FF] text-white' : 'bg-gray-100 text-gray-400'}`}
                >
                  {c}
                </button>
              ))}
            </div>
          </section>

          {/* Budget Range slider */}
          <section className="space-y-8">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-gray-900 text-lg">비용 (예상 총액)</h3>
              <p className="text-[#0066FF] font-black text-lg">{budget[0]}만원 ~ {budget[1]}만원</p>
            </div>
            <div className="px-2 relative h-10 flex items-center">
              {/* Dual Range Track */}
              <div className="absolute inset-0 mx-2 h-1.5 bg-blue-50 rounded-full top-[18px]">
                <div
                  className="absolute h-full bg-[#0066FF] rounded-full"
                  style={{
                    left: `${((budget[0] - 5) / 45) * 100}%`,
                    right: `${100 - ((budget[1] - 5) / 45) * 100}%`
                  }}
                />
              </div>
              {/* Invisible Range Inputs for Interaction */}
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
                className="absolute w-full h-10 appearance-none bg-transparent pointer-events-none z-30 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-10 [&::-webkit-slider-thumb]:h-10 [&::-webkit-slider-thumb]:bg-transparent [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:w-10 [&::-moz-range-thumb]:h-10 [&::-moz-range-thumb]:bg-transparent"
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
                className="absolute w-full h-10 appearance-none bg-transparent pointer-events-none z-30 [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-10 [&::-webkit-slider-thumb]:h-10 [&::-webkit-slider-thumb]:bg-transparent [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:w-10 [&::-moz-range-thumb]:h-10 [&::-moz-range-thumb]:bg-transparent"
              />
              {/* Visual Handles */}
              <div
                className="absolute w-6 h-6 bg-white border-4 border-[#0066FF] rounded-full shadow-lg pointer-events-none transition-transform active:scale-125"
                style={{ left: `calc(${((budget[0] - 5) / 45) * 100}% - 12px + 8px)` }}
              />
              <div
                className="absolute w-6 h-6 bg-white border-4 border-[#0066FF] rounded-full shadow-lg pointer-events-none transition-transform active:scale-125"
                style={{ left: `calc(${((budget[1] - 5) / 45) * 100}% - 12px + 8px)` }}
              />
            </div>
            <div className="flex justify-between items-center px-2 text-[10px] font-black text-gray-300 uppercase tracking-widest">
              <span>5만원</span>
              <span>50만원</span>
            </div>
          </section>

          <div className="flex flex-col gap-4">
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
              className="w-full py-6 bg-gradient-to-r from-[#0066FF] to-blue-500 text-white rounded-2xl font-black text-xl shadow-xl shadow-blue-100 active:scale-[0.98] transition-all flex items-center justify-center gap-3"
            >
              코스 생성 확인하기
            </button>
            <button
              onClick={() => router.push('/chat')}
              className="w-full py-5 bg-gray-100 text-gray-400 rounded-2xl font-bold text-base active:scale-[0.95] transition-all flex items-center justify-center gap-2"
            >
              바로 채팅으로 가기
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
