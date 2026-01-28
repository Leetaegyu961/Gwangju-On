"use client";

import React from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { MessageSquare, Map as MapIcon, User } from 'lucide-react';

export const Navigation = () => {
  const pathname = usePathname();
  const router = useRouter();

  // 온보딩이나 로그인 단계에서는 숨김
  if (pathname === '/' || pathname === '/login' || pathname === '/onboarding') return null;

  const tabs = [
    { id: 'guide', label: 'AI 가이드', path: '/survey', icon: MessageSquare, isAI: true, activePaths: ['/survey', '/chat'] },
    { id: 'map', label: '지도', path: '/map', icon: MapIcon },
    { id: 'profile', label: '마이페이지', path: '/profile', icon: User },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 px-10 py-2 flex justify-between items-center z-[500] pb-8 shadow-[0_-10px_40px_rgba(0,0,0,0.03)]">
      {tabs.map((tab) => {
        const isActive = tab.activePaths
          ? tab.activePaths.includes(pathname)
          : pathname === tab.path;
        const Icon = tab.icon;

        return (
          <button
            key={tab.id}
            onClick={() => router.push(tab.path)}
            className={`flex flex-col items-center gap-1.5 transition-all flex-1 ${isActive ? 'text-[#0066FF]' : 'text-gray-300'}`}
          >
            <div className="relative p-1">
              <Icon size={26} strokeWidth={isActive ? 2.5 : 2} />
              {tab.isAI && (
                <div className={`absolute -top-1 -right-3 text-[9px] font-black px-1.5 py-0.5 rounded-[4px] shadow-sm ${isActive ? 'bg-[#0066FF] text-white' : 'bg-gray-100 text-gray-400'}`}>
                  AI
                </div>
              )}
            </div>
            <span className={`text-[11px] font-black tracking-tight ${isActive ? 'opacity-100' : 'opacity-70'}`}>
              {tab.label}
            </span>
            {isActive && (
              <div className="w-1 h-1 bg-[#0066FF] rounded-full mt-0.5 animate-fade-in" />
            )}
          </button>
        );
      })}
    </nav>
  );
};
