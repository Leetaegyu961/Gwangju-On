
"use client";

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Bot, Mic, ArrowLeft, Send } from 'lucide-react';
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
  const [streamProgress, setStreamProgress] = useState<{step: string; message: string; progress: number; icon?: string} | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const invalidMsg = searchParams.get('invalidMsg');

    if (isLocationRequestMode || searchParams.get('mode') === 'course_init') {
      const initialMessages: Message[] = [
        {
          id: '1',
          role: 'assistant',
          text: '가고 싶은 장소가 있나요?',
          suggestions: ['바로 코스 생성하기']
        }
      ];

      // MapView에서 유효하지 않은 입력으로 되돌아온 경우
      if (invalidMsg) {
        initialMessages.push({
          id: `invalid_redirect_${Date.now()}`,
          role: 'assistant',
          text: decodeURIComponent(invalidMsg),
          showSurveyPrompt: true,
          suggestions: ['바로 코스 생성하기']
        });
      }

      setMessages(initialMessages);
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
    if (isLocationRequestMode) {
      const locationMsg = messages.find(m => m.role === 'user');
      if (locationMsg && !input.includes(locationMsg.text)) {
        fullInput = `${locationMsg.text}에 있는 ${input}`;
      }
    }

    setInput('');
    setLoading(true);

    // 입력 유효성 검증
    try {
      const validation = await aiService.validateInput(fullInput);
      if (!validation.isValid) {
        setLoading(false);
        // 유효하지 않은 입력 → 채팅에서 안내 메시지 + 설문 기반 코스 생성 유도
        setMessages(prev => [...prev, {
          id: `invalid_${Date.now()}`,
          role: 'assistant' as const,
          text: validation.message,
          showSurveyPrompt: true,
          suggestions: ['바로 코스 생성하기']
        }]);
        return;
      }
    } catch (e) {
      // 검증 실패 시 그냥 진행
      console.warn('[ChatScreen] Validation failed, proceeding:', e);
    }

    setLoading(false);

    // "코스 생성을 시작합니다!" 메시지 표시 후 MapView로 이동 (통합 로딩 UX)
    setMessages(prev => [...prev, {
      id: 'generating',
      role: 'assistant',
      text: '네! 코스 생성을 시작합니다! 🎯'
    }]);

    const userId = localStorage.getItem('temp_user_id');
    const encodedPrompt = encodeURIComponent(fullInput);
    setTimeout(() => {
      router.push(`/map?auto_generate=true&userId=${userId}&prompt=${encodedPrompt}`);
    }, 800);
  };

  return (
    <div className="h-screen bg-[#FDFDFD] flex flex-col font-['Inter'] overflow-hidden">
      {/* Header */}
      <header className="bg-white px-6 py-5 flex items-center justify-between sticky top-0 z-[100] border-b border-gray-50 shadow-sm">
        <button onClick={() => router.push('/survey')} className="p-1 -ml-1 text-gray-400">
          <ArrowLeft size={24} />
        </button>
        <h1 className="text-xl font-bold text-gray-800 tracking-tight">AI 가이드</h1>
        <div className="w-8" />
      </header>

      {/* Chat Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-10 hide-scrollbar pb-60">
        {messages.map((m) => (
          <div key={m.id} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}>
            {m.role === 'assistant' && (
              <div className="w-10 h-10 rounded-full flex items-center justify-center shadow-md mb-3 overflow-hidden bg-white border border-gray-100 shrink-0">
                <img src="/mascot_circle.png" alt="Assistant" className="w-full h-full object-cover" />
              </div>
            )}

            {/* 텍스트 메시지 표시 (코스 결과가 나온 경우 텍스트 숨기고 바로 이동하므로, 결정 포인트가 아닐 때만 표시하거나, 로딩처럼 처리) */}
            {(!m.isDecisionPoint || m.id === 'err') && (
              <div className={`p-5 rounded-[2rem] text-[15px] font-bold leading-relaxed max-w-[85%] shadow-sm ${m.role === 'user'
                ? 'bg-[#E9F1FF] text-[#1E6BFF] rounded-tr-none'
                : 'bg-[#F2F2F2] text-gray-800 rounded-tl-none'
                }`}>
                {m.text}
              </div>
            )}

            {/* 코스 결과가 나왔을 때 (isDecisionPoint) - 사용자에게 묻지 않고 바로 이동 */}
            {m.isDecisionPoint && (
              <div className="p-5 bg-blue-50 text-[#0066FF] rounded-2xl font-bold text-sm animate-pulse">
                코스를 생성했습니다! 지도로 이동합니다...
                {/* 자동 이동 로직은 useEffect에서 처리 */}
              </div>
            )}

            {/* Suggestions Chips & Inputs */}
            {m.suggestions && (
              <div className="mt-4 flex flex-col gap-3 w-full animate-fade-in">
                {m.suggestions.map((suggestion, idx) => {
                  if (suggestion === '바로 코스 생성하기') {
                    return (
                      <div key={idx} className="w-full flex flex-col gap-2">
                        {/* 설문조사 기반 코스 생성 유도 메시지 */}
                        {m.showSurveyPrompt && (
                          <p className="text-center text-sm text-gray-500 animate-pulse py-1">
                            설문조사 기반으로 바로 코스를 생성해드릴까요?
                          </p>
                        )}
                        {/* Primary Action Button */}
                        <button
                          onClick={() => {
                             // 1. 사용자 메시지 추가 (UI 피드백)
                             const userMsg: Message = { id: Date.now().toString(), role: 'user', text: suggestion };
                             setMessages(prev => [...prev, userMsg]);

                             // 2. 즉시 페이지 이동 (PRD v2.1) + 추가 요청사항 전달
                             // Use 'input' state from the bottom bar
                             const userId = localStorage.getItem('temp_user_id');
                             const extraQuery = input.trim() ? `&extraRequest=${encodeURIComponent(input)}` : '';
                             router.push(`/map?auto_generate=true&userId=${userId}${extraQuery}`);
                          }}
                          className="w-full py-4 bg-[#0066FF] text-white rounded-2xl font-bold text-base shadow-lg shadow-blue-200 active:scale-95 transition-all flex items-center justify-center gap-2"
                        >
                          <span className="text-lg">✨</span> {suggestion}
                        </button>
                      </div>
                    );
                  }

                  return (
                  <button
                    key={idx}
                    onClick={() => {
                      // [Branching Logic] "가고 싶은 장소가 있나요?" 에 대한 처리 (Legacy check removed)

                      // 칩 클릭 시 바로 전송 처리
                      const userMsg: Message = { id: Date.now().toString(), role: 'user', text: suggestion };
                      setMessages(prev => [...prev, userMsg]);

                      // 위치 선택 단계였다면 -> 요구사항 물어보는 단계로 진행
                      if (messages.length === 1 && isLocationRequestMode) {
                        setTimeout(() => {
                          setMessages(prev => [...prev, {
                            id: 'req_ask',
                            role: 'assistant',
                            text: `${suggestion}에서 특별히 원하시는 테마나 메뉴가 있으신가요?\n(예: 조용한 데이트 코스, 가성비 맛집 등)`
                          }]);
                        }, 500);
                        return; // API 호출 안 함
                      }

                      // 그 외의 경우 (요구사항 칩 등) -> MapView 통합 로딩으로 이동
                      const lastLocation = messages.find(msg => msg.role === 'user')?.text || "";
                      const fullQuery = lastLocation ? `${lastLocation} ${suggestion}` : suggestion;

                      setMessages(prev => [...prev, {
                        id: 'generating',
                        role: 'assistant',
                        text: '네! 코스 생성을 시작합니다! 🎯'
                      }]);

                      const chipUserId = localStorage.getItem('temp_user_id');
                      const chipPrompt = encodeURIComponent(fullQuery);
                      setTimeout(() => {
                        router.push(`/map?auto_generate=true&userId=${chipUserId}&prompt=${chipPrompt}`);
                      }, 800);
                    }}
                    className="px-5 py-3 bg-white border border-[#0066FF]/20 text-[#0066FF] rounded-2xl font-bold text-sm shadow-sm hover:bg-blue-50 active:scale-95 transition-all"
                  >
                    {suggestion}
                  </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-3 animate-fade-in">
            <div className="w-10 h-10 rounded-full overflow-hidden bg-white shadow-sm border border-blue-50 animate-bounce shrink-0">
              <img src="/mascot_circle.png" alt="Loading" className="w-full h-full object-cover" />
            </div>
            <div className="bg-white px-5 py-3 rounded-[2rem] rounded-tl-none shadow-sm border border-gray-100">
              <span className="text-xs font-bold text-gray-400">준비 중...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 bg-white absolute bottom-24 left-0 right-0 z-[110] border-t border-gray-50">
        <div className="flex items-center border-2 border-gray-100 rounded-[2rem] px-6 py-4 transition-all focus-within:border-blue-300">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSend()}
            placeholder={
              messages.length > 0 && messages[messages.length - 1].suggestions?.includes('바로 코스 생성하기')
                ? "추가로 원하시는 요청사항이 있다면 입력해주세요. (예: 조용한 분위기, 주차 편한 곳)"
                : "프롬프트를 입력하세요..."
            }
            className="flex-1 bg-transparent outline-none font-bold text-gray-700 placeholder:text-gray-300 text-base"
          />
          <button
            onClick={handleSend}
            className="w-12 h-12 bg-[#0066FF] rounded-full flex items-center justify-center text-white shadow-lg active:scale-90 transition-all shrink-0 ml-2"
          >
            <Send size={20} className="ml-0.5" />
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