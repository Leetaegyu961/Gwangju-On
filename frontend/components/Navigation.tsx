"use client";

import React from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { MessageSquare, Map as MapIcon, User, Camera } from 'lucide-react';

export const Navigation = () => {
  const pathname = usePathname();
  const router = useRouter();

  // 온보딩이나 로그인 단계에서는 숨김
  if (pathname === '/' || pathname === '/login' || pathname === '/onboarding') return null;

  const tabs = [
    { id: 'guide', label: 'AI 가이드', path: '/survey', icon: MessageSquare, isAI: true, activePaths: ['/survey', '/chat'] },
    { id: 'map', label: '지도', path: '/map', icon: MapIcon },
    { id: 'timeline', label: '타임라인', path: '/timeline', icon: Camera },
    { id: 'profile', label: '마이페이지', path: '/profile', icon: User },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 px-6 py-3 flex justify-around items-center z-[500] pb-6 shadow-[0_-10px_30px_rgba(0,0,0,0.02)]">
      {tabs.map((tab) => {
        const isActive = tab.activePaths
          ? tab.activePaths.includes(pathname)
          : pathname === tab.path;
        const Icon = tab.icon;

        return (
          <button
            key={tab.id}
            onClick={() => router.push(tab.path)}
            className={`flex flex-col items-center gap-1 transition-all w-16 ${isActive ? 'text-[#0066FF] scale-105' : 'text-gray-300 hover:text-gray-400'}`}
          >
            <div className="relative p-0.5">
              <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
              {tab.isAI && (
                <div className={`absolute -top-1 -right-2.5 text-[8px] font-black px-1 py-0.5 rounded-[3px] shadow-sm ${isActive ? 'bg-[#0066FF] text-white' : 'bg-gray-100 text-gray-400'}`}>
                  AI
                </div>
              )}
            </div>
            <span className={`text-[10px] font-bold tracking-tight ${isActive ? 'opacity-100' : 'opacity-70'}`}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
};
