
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
    if (isLocationRequestMode) {
      setMessages([
        {
          id: '1',
          role: 'assistant',
          text: '어디 위치를 원하세요?',
          suggestions: ['광주 광역시 동명동', '광주 광역시 광산구', '광주 전체']
        }
      ]);
    } else {
      // Normal entry
      setMessages([
        { id: '1', role: 'assistant', text: '안녕하세요! 어떤 여행을 도와드릴까요?' }
      ]);
    }
  }, [isLocationRequestMode]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.isDecisionPoint && lastMsg.evidenceCards) {
      // 자동 코스 생성 및 이동
      const courses = lastMsg.evidenceCards.map((c, i) => ({
        id: c.placeId || i.toString(),
        name: c.name || c.placeId,
        lat: c.lat || 0,
        lng: c.lng || 0,
        desc: c.reason,
        tags: c.keywords || [],
        transport: '이동',
        img: c.img || getCourseImage(c.keywords, c.name)
      }));
      localStorage.setItem('current_course', JSON.stringify(courses));

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
              <div className="w-10 h-10 bg-[#0066FF] rounded-full flex items-center justify-center shadow-lg mb-3">
                <Bot size={22} className="text-white" />
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

            {/* Suggestions Chips */}
            {m.suggestions && (
              <div className="mt-4 flex flex-wrap gap-2 animate-fade-in">
                {m.suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
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

                      // 그 외의 경우 (요구사항 칩 등) -> API 호출
                      setLoading(true);
                      setTimeout(async () => {
                        try {
                          // 이전 대화 맥락을 포함해서 보내야 하지만, 현재 API 구조상 input만 보냄. 
                          // 실제로는 "광주 동명동 + 조용한 데이트 코스" 형태로 합쳐서 보내거나 Context를 유지해야 함.
                          // 여기서는 편의상 입력값만 보냄. (개선 필요: 위치 정보를 기억했다가 같이 보냄)

                          // *임시 해결*: 이전 메시지(위치)를 찾아서 결합
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
                    className="px-5 py-3 bg-white border border-[#0066FF]/20 text-[#0066FF] rounded-2xl font-bold text-sm shadow-sm hover:bg-blue-50 active:scale-95 transition-all"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="p-4 bg-gray-50 rounded-2xl self-start animate-pulse text-xs font-bold text-gray-400">최적의 코스를 찾는 중입니다...</div>}
      </div>

      {/* Input Area */}
      <div className="p-6 bg-white absolute bottom-24 left-0 right-0 z-[110] border-t border-gray-50">
        <div className="flex items-center border-2 border-gray-100 rounded-[2rem] px-6 py-4 transition-all focus-within:border-blue-300">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSend()}
            placeholder="프롬프트를 입력하세요..."
            className="flex-1 bg-transparent outline-none font-bold text-gray-700 placeholder:text-gray-300 text-base"
          />
          <button
            onClick={handleSend}
            className="w-12 h-12 bg-[#0066FF] rounded-full flex items-center justify-center text-white shadow-lg active:scale-90 transition-all shrink-0 ml-2"
          >
            <Mic size={24} />
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
