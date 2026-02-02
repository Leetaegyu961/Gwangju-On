
"use client";

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Bot, Mic, ArrowLeft } from 'lucide-react';
import { GeminiService } from '../services/geminiService';
import { Message } from '../types';
import { getCourseImage } from '../utils/courseImages';

const aiService = new GeminiService();

const ChatContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isLocationRequestMode = searchParams.get('mode') === 'location_request';

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isLocationRequestMode || searchParams.get('mode') === 'course_init') {
      setMessages([
        {
          id: '1',
          role: 'assistant',
          text: '가고 싶은 장소가 있나요?',
          suggestions: ['네, 계속 채팅하기', '아니요, 바로 코스 생성하기']
        }
      ]);
    } else {
      // Normal entry
      setMessages([
        { id: '1', role: 'assistant', text: '안녕하세요! 어떤 여행을 도와드릴까요?' }
      ]);
    }
  }, [isLocationRequestMode, searchParams]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.isDecisionPoint && lastMsg.evidenceCards) {

      // 1. 코스 데이터 생성 (이미지 URL 확정)
      const courses = lastMsg.evidenceCards.map((c, i) => ({
        id: c.placeId || i.toString(),
        type: '놀거리' as const,
        name: c.name || c.placeId,
        lat: c.lat || 0,
        lng: c.lng || 0,
        desc: c.reason,
        tags: c.keywords || [],
        transport: '이동',
        img: c.img || getCourseImage(c.keywords, c.name) // Generate URL ONCE
      }));

      // 2. 전체 후보 코스 데이터 생성 (이미지 URL 확정)
      let allCoursesForMap: any[] = [];
      if (lastMsg.allCourses && lastMsg.allCourses.length > 0) {
        allCoursesForMap = lastMsg.allCourses.map(course => ({
          course_id: course.course_id,
          course_name: course.course_name,
          course_description: course.course_description || '',
          places: course.cards.map((c, i) => ({
            id: c.placeId || i.toString(),
            type: '놀거리',
            name: c.name || c.placeId,
            lat: c.lat || 0,
            lng: c.lng || 0,
            desc: c.reason,
            tags: c.keywords || [],
            transport: '이동',
            img: c.img || getCourseImage(c.keywords, c.name) // Generate URL ONCE
          }))
        }));
      }

      // 3. [Performance] 확정된 URL로 이미지 미리 로딩 (Preloading)
      const preloadImages = () => {
        const urlsToLoad = new Set<string>();

        // 현재 코스 이미지
        courses.forEach(c => {
          if (c.img) urlsToLoad.add(c.img);
        });

        // 전체 후보 코스 이미지
        allCoursesForMap.forEach(course => {
          course.places.forEach((p: any) => {
            if (p.img) urlsToLoad.add(p.img);
          });
        });

        // 브라우저 캐시에 이미지 저장
        urlsToLoad.forEach(url => {
          const img = new Image();
          img.src = url;
        });
        console.log(`[Preload] Preloaded ${urlsToLoad.size} images.`);
      };
      preloadImages();

      // 4. 저장 (localStorage)
      localStorage.setItem('current_course', JSON.stringify(courses));
      if (allCoursesForMap.length > 0) {
        localStorage.setItem('all_courses', JSON.stringify(allCoursesForMap));
      }

      // DB/History에 영구 저장
      const savedCourse = {
        id: Date.now().toString(),
        userId: localStorage.getItem('temp_user_id') || '',
        title: `AI 추천 코스 (${new Date().toLocaleDateString()})`,
        points: courses,
        totalBudget: '예산 미정',
        createdAt: new Date().toISOString(),
        description: lastMsg.text?.substring(0, 100) + '...' || 'AI가 생성한 맞춤형 여행 코스입니다.'
      };
      aiService.saveCourse(savedCourse);

      // 잠시 후 이동 (사용자가 메시지를 볼 시간 1초)
      const timer = setTimeout(() => {
        router.push('/map');
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [messages, router]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { id: Date.now().toString(), role: 'user', text: input };
    setMessages(prev => [...prev.map(m => ({ ...m, isDecisionPoint: false })), userMsg]);

    let fullInput = input;
    // 이전 대화 맥락(특히 위치 정보)을 포함하여 전송
    if (isLocationRequestMode) {
      const locationMsg = messages.find(m => m.role === 'user');
      if (locationMsg && !input.includes(locationMsg.text)) {
        fullInput = `${locationMsg.text}에 있는 ${input}`;
      }
    }

    setInput('');
    setLoading(true);

    try {
      const response = await aiService.processRequest(fullInput);
      setMessages(prev => [...prev, response]);
    } catch (err) {
      setMessages(prev => [...prev, { id: 'err', role: 'assistant', text: '오류가 발생했습니다.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen bg-[#FDFBF7] flex flex-col font-['Inter'] overflow-hidden">
      {/* Header - Soft Style */}
      <header className="bg-white/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-[100] border-b border-gray-100">
        <button onClick={() => router.push('/survey')} className="p-2 -ml-2 text-gray-400 hover:text-gray-600 transition-colors">
          <ArrowLeft size={24} />
        </button>
        <div className="flex flex-col items-center">
          <h1 className="text-lg font-bold text-gray-800">AI 큐레이터</h1>
          <span className="text-[10px] items-center gap-1 text-[#0066FF] font-medium flex">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
            Online
          </span>
        </div>
        <div className="w-8" />
      </header>

      {/* Chat Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-8 hide-scrollbar pb-60">
        {messages.map((m) => (
          <div key={m.id} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}>
            {m.role === 'assistant' && (
              <div className="w-14 h-14 bg-white rounded-full flex items-center justify-center shadow-md border border-orange-50 mb-2 overflow-hidden relative shrink-0">
                <img src="/mascot_circle.png" className="w-full h-full object-cover scale-110" alt="mascot" />
              </div>
            )}

            {/* Message Bubble - Warm Style */}
            {(!m.isDecisionPoint || m.id === 'err') && (
              <div className={`p-5 rounded-[2rem] text-[15px] leading-relaxed max-w-[85%] shadow-sm border ${m.role === 'user'
                ? 'bg-[#0066FF] text-white rounded-tr-none border-[#0066FF]'
                : 'bg-white text-gray-700 rounded-tl-none border-gray-100 font-medium'
                }`}>
                {m.text}
              </div>
            )}

            {/* Decision Point Style */}
            {m.isDecisionPoint && (
              <div className="p-5 bg-white text-[#0066FF] rounded-2xl font-bold text-sm animate-pulse border border-blue-100 shadow-sm">
                ✨ 코스를 완성했습니다! 지도로 이동합니다...
              </div>
            )}

            {/* Suggestions Chips - Warm Style */}
            {m.suggestions && (
              <div className="mt-3 flex flex-wrap gap-2 animate-fade-in pl-1">
                {m.suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      if (suggestion === '아니요, 바로 코스 생성하기') {
                        const userMsg: Message = { id: Date.now().toString(), role: 'user', text: suggestion };
                        setMessages(prev => [...prev, userMsg]);
                        const userId = localStorage.getItem('temp_user_id');
                        router.push(`/map?auto_generate=true&userId=${userId}`);
                        return;
                      }

                      const userMsg: Message = { id: Date.now().toString(), role: 'user', text: suggestion };
                      setMessages(prev => [...prev, userMsg]);

                      if (messages.length === 1 && isLocationRequestMode) {
                        setTimeout(() => {
                          setMessages(prev => [...prev, {
                            id: 'req_ask',
                            role: 'assistant',
                            text: `${suggestion}에서 특별히 원하시는 테마나 메뉴가 있으신가요?\n(예: 조용한 데이트 코스, 가성비 맛집 등)`
                          }]);
                        }, 500);
                        return;
                      }

                      setLoading(true);
                      setTimeout(async () => {
                        try {
                          const lastLocation = messages.find(msg => msg.role === 'user')?.text || "";
                          const fullQuery = lastLocation ? `${lastLocation} ${suggestion}` : suggestion;
                          const response = await aiService.processRequest(fullQuery);
                          setMessages(prev => [...prev, response]);
                        } catch (e) {
                          setMessages(prev => [...prev, { id: 'err', role: 'assistant', text: '오류가 발생했습니다.' }]);
                        } finally {
                          setLoading(false);
                        }
                      }, 100);
                    }}
                    className="px-5 py-2.5 bg-white border border-gray-200 text-gray-600 rounded-full font-bold text-sm shadow-sm hover:border-[#0066FF] hover:text-[#0066FF] hover:bg-blue-50/50 active:scale-95 transition-all"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-3 ml-2 animate-fade-in">
            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-md border border-orange-50 relative overflow-hidden animate-bounce">
              <img src="/mascot_circle.png" className="w-full h-full object-cover scale-110" alt="loading mascot" />
            </div>
            <div className="p-3 bg-white border border-gray-100 rounded-2xl rounded-tl-none shadow-sm text-xs font-bold text-gray-500">
              💭 열심히 코스를 짜고 있어요!
            </div>
          </div>
        )}
      </div>

      {/* Input Area - Warm Style */}
      <div className="p-6 bg-[#FDFBF7] absolute bottom-24 left-0 right-0 z-[110]">
        <div className="flex items-center bg-white border border-gray-200 rounded-[2rem] px-5 py-3 transition-all focus-within:border-[#0066FF] focus-within:ring-4 focus-within:ring-blue-50/50 shadow-sm">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSend()}
            placeholder="어떤 여행을 원하시나요?"
            className="flex-1 bg-transparent outline-none font-medium text-gray-700 placeholder:text-gray-400 text-base"
          />
          <button
            onClick={handleSend}
            className="w-10 h-10 bg-[#0066FF] rounded-full flex items-center justify-center text-white shadow-md active:scale-90 transition-all shrink-0 ml-2 hover:bg-[#0052cc]"
          >
            <Mic size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export const ChatScreen = () => (
  <Suspense fallback={<div className="h-screen bg-white flex items-center justify-center font-bold">대화창을 불러오는 중...</div>}>
    <ChatContent />
  </Suspense>
);