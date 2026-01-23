
"use client";

import React from 'react';
import { useRouter } from 'next/navigation';

/**
 * [Image 0 Reference: Clean White Login with Mascot]
 */
export const LoginScreen = () => {
  const router = useRouter();

  // 구글 로그인 연동 준비
  const handleGoogleLogin = () => {
    if (typeof window !== 'undefined' && (window as any).google) {
      (window as any).google.accounts.id.initialize({
        client_id: "117313124086-rc4e20pfeo597aqolshtspeunsh3hmh3.apps.googleusercontent.com",
        callback: (response: any) => {
          console.log("Google Login Response:", response);
          // TODO: 백엔드(몽고DB) 연동 및 JWT 처리
          router.push('/onboarding?mode=google');
        }
      });
      (window as any).google.accounts.id.prompt();
    } else {
      // 스크립트 로드 대기 또는 예외 처리
      handleStart('google');
    }
  };

  const handleStart = (mode: 'google' | 'guest') => {
    if (mode === 'google') {
      handleGoogleLogin();
    } else {
      router.push(`/onboarding?mode=${mode}`);
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-6 font-['Inter'] relative">

      {/* Mascot Illustration Area (Image 0) */}
      <div className="flex flex-col items-center mb-16 animate-fade-in">
        <div className="w-64 h-64 mb-10 flex items-center justify-center relative">
          {/* Replicating the mascot mountain character from Image 0 */}
          <img
            src="https://img.freepik.com/free-vector/cute-mountain-character-illustration_23-2148766126.jpg?w=740"
            className="w-full h-full object-contain"
            alt="ONui Mascot"
          />
          {/* Optional: Add a subtle shadow under the mascot */}
          <div className="absolute bottom-4 w-32 h-4 bg-gray-100 rounded-full blur-md -z-10" />
        </div>
      </div>

      {/* Action Area (Image 0) */}
      <div className="w-full max-w-[340px] flex flex-col items-center gap-6 animate-fade-in" style={{ animationDelay: '0.2s' }}>
        <button
          onClick={() => handleStart('google')}
          className="w-full py-4 bg-[#3A7BFF] text-white rounded-[2rem] font-bold shadow-lg shadow-blue-100 flex items-center justify-center gap-4 active:scale-[0.98] transition-all"
        >
          <div className="bg-white p-1.5 rounded-full">
            <img src="https://www.gstatic.com/images/branding/product/1x/gsa_512dp.png" className="w-5 h-5" alt="G" />
          </div>
          <span className="text-lg tracking-tight">구글 계정으로 로그인</span>
        </button>

        <button
          onClick={() => handleStart('guest')}
          className="text-base font-bold text-gray-500 hover:text-gray-800 transition-colors"
        >
          계정 없이 시작하기
        </button>
      </div>

      {/* Invisible Spacer for vertical alignment matching Image 0 */}
      <div className="h-20" />
    </div>
  );
};
