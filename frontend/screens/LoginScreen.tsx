"use client";

import Script from 'next/script';
import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

export const LoginScreen = () => {
  const router = useRouter();
  const [isSdkReady, setIsSdkReady] = useState(false);
  const isInitialized = useRef(false);
  const isPrompting = useRef(false);

  const initializeGoogleSdk = () => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    if (typeof window !== 'undefined' && (window as any).google && !isInitialized.current) {
      if (!clientId) {
        console.error("NEXT_PUBLIC_GOOGLE_CLIENT_ID is not defined in .env.local");
        return;
      }

      (window as any).google.accounts.id.initialize({
        client_id: clientId,
        use_fedcm_for_prompt: true, // 최신 보안 표준 활성화
        callback: async (response: any) => {
          console.log("Google Auth successful");
          try {
            const guestId = localStorage.getItem('temp_user_id');
            const res = await fetch(`${apiUrl}/api/auth/google`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                id_token: response.credential,
                guest_id: guestId
              }),
            });

            if (!res.ok) throw new Error('Backend failure');

            const data = await res.json();
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            localStorage.setItem('temp_user_id', data.user.id);
            router.push('/home');
          } catch (error) {
            console.error("Login verification error:", error);
            alert("로그인 확인 중 오류가 발생했습니다.");
          }
        }
      });

      // 가장 확실한 작동을 위해 버튼 렌더링 추가
      const buttonDiv = document.getElementById("google-button-div");
      if (buttonDiv) {
        (window as any).google.accounts.id.renderButton(buttonDiv, {
          theme: "outline",
          size: "large",
          width: 340,
          text: "signin_with",
          shape: "pill"
        });
      }

      isInitialized.current = true;
      setIsSdkReady(true);
      console.log("✅ Google SDK Ready (FedCM active)");
    }
  };

  useEffect(() => {
    if ((window as any).google && !isInitialized.current) {
      initializeGoogleSdk();
    }
  }, []);

  const handleGoogleLogin = () => {
    if (!isSdkReady) {
      alert("로그인 초기화 중입니다. 잠시 후 버튼을 다시 눌러주세요.");
      return;
    }

    if (typeof window !== 'undefined' && (window as any).google) {
      if (isPrompting.current) return;
      isPrompting.current = true;

      // 최신 권장사항: 구식 상태 메소드 없이 최소한으로 호출
      (window as any).google.accounts.id.prompt(() => {
        isPrompting.current = false;
      });
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
      <Script
        src="https://accounts.google.com/gsi/client"
        onLoad={initializeGoogleSdk}
        strategy="afterInteractive"
      />

      <div className="flex flex-col items-center mb-16 animate-fade-in">
        <div className="w-64 h-64 mb-10 flex items-center justify-center relative">
          <img
            src="https://img.freepik.com/free-vector/cute-mountain-character-illustration_23-2148766126.jpg?w=740"
            className="w-full h-full object-contain"
            alt="ONui Mascot"
          />
          <div className="absolute bottom-4 w-32 h-4 bg-gray-100 rounded-full blur-md -z-10" />
        </div>
      </div>

      <div className="w-full max-w-[340px] flex flex-col items-center gap-6 animate-fade-in" style={{ animationDelay: '0.2s' }}>
        {/* 구글 로그인 버튼 렌더링 영역 */}
        <div id="google-button-div" className="w-full min-h-[50px]"></div>

        <button
          onClick={() => handleStart('guest')}
          className="text-base font-bold text-gray-500 hover:text-gray-800 transition-colors"
        >
          계정 없이 시작하기
        </button>
      </div>

      <div className="h-20" />
    </div>
  );
};
