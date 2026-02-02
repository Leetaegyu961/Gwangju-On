
"use client";

import React, { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

/**
 * [Image 0 Reference: Clean White Login with Mascot]
 */
export const LoginScreen = () => {
    const router = useRouter();
    const googleButtonRef = useRef<HTMLDivElement>(null);

    // 구글 로그인 성공 콜백
    const handleCredentialResponse = async (response: any) => {
        console.log("Google Login Response:", response);

        // 백엔드로 토큰 전송하여 검증 및 로그인 처리
        try {
            // 게스트 ID 획득 (데이터 마이그레이션용)
            const guest_id = localStorage.getItem('temp_user_id') || undefined;

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id_token: response.credential,
                    guest_id: guest_id
                })
            });

            if (res.ok) {
                const data = await res.json();
                console.log("✅ Login Success:", data);
                // 토큰 저장
                localStorage.setItem('access_token', data.access_token);
                if (data.user && data.user.id) {
                    localStorage.setItem('temp_user_id', data.user.id);
                    // 프로필 정보 즉시 저장 (마이페이지 깜빡임 방지)
                    localStorage.setItem('user_profile', JSON.stringify(data.user));
                }

                // 온보딩 여부에 따라 이동
                if (data.user.is_onboarded) {
                    router.push('/map'); // or main
                } else {
                    router.push('/survey');
                }
            } else {
                console.error("Login Failed");
                alert("로그인에 실패했습니다.");
            }
        } catch (e) {
            console.error("Login Error", e);
            alert("서버와 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인해주세요.");
        }
    };

    useEffect(() => {
        // [Debug] Environment Checks
        console.log("🔍 Debug Info:");
        console.log("   - Origin:", window.location.origin);
        console.log("   - User Agent:", navigator.userAgent);

        // 구글 로그인 버튼 렌더링
        const initializeGoogleSignIn = (retryCount = 0) => {
            if (typeof window !== 'undefined' && (window as any).google && googleButtonRef.current) {
                try {
                    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

                    if (!clientId) {
                        console.error("Google Client ID is missing");
                        return;
                    }

                    // Cooldown reset for testing
                    document.cookie = `g_state=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT`;

                    console.log("   - Client ID used:", clientId);
                    (window as any).google.accounts.id.initialize({
                        client_id: clientId,
                        callback: handleCredentialResponse,
                        use_fedcm_for_prompt: true,
                        itp_support: true,
                    });

                    // 렌더링 (커스텀 버튼 스타일을 최대한 대체)
                    (window as any).google.accounts.id.renderButton(
                        googleButtonRef.current,
                        {
                            theme: 'filled_blue',
                            size: 'large',
                            width: '340', // 부모 컨테이너와 동일하게
                            shape: 'pill',
                            text: 'signin_with',
                            locale: 'ko'
                        }
                    );

                    // One Tap도 함께 띄우기 (선택사항)
                    (window as any).google.accounts.id.prompt();
                } catch (e) {
                    console.error("GSI Init Error:", e);
                }
            } else {
                if (retryCount < 10) {
                    setTimeout(() => initializeGoogleSignIn(retryCount + 1), 500);
                }
            }
        };

        initializeGoogleSignIn();
    }, []);

    const handleStart = (mode: 'guest') => {
        router.push(`/onboarding?mode=${mode}`);
    };

    return (
        <div className="min-h-screen bg-[#FFFDF8] flex flex-col items-center justify-center p-6 font-['Inter'] relative overflow-hidden">
            {/* Background Decorations */}
            <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
                <div className="absolute top-[-10%] right-[-10%] w-80 h-80 bg-orange-100/40 rounded-full blur-3xl opacity-60" />
                <div className="absolute bottom-[-5%] left-[-10%] w-64 h-64 bg-yellow-100/40 rounded-full blur-3xl opacity-60" />
            </div>

            <div className="w-full max-w-[340px] flex flex-col items-center relative z-10">
                {/* Title Section */}
                <div className="text-center mb-8 animate-fade-in">
                    <div className="inline-block px-3 py-1 bg-white border border-orange-100 rounded-full shadow-sm mb-4">
                        <span className="text-[10px] font-bold text-orange-500 tracking-wider">GWANGJU-ON</span>
                    </div>
                    <h1 className="text-[28px] font-black text-gray-900 leading-[1.3] mb-2">
                        여행의 설렘을<br />
                        <span className="text-[#FF6B00]">광주-온</span>에서 시작해봐!
                    </h1>
                    <p className="text-gray-400 text-sm font-medium">
                        AI 큐레이터가 당신만의 여행을 돕습니다
                    </p>
                </div>

                {/* Mascot Hero Image */}
                {/* Mascot Hero Video */}
                <div className="relative w-72 h-72 mb-8 flex items-center justify-center">
                    {/* Background Glow */}
                    <div className="absolute inset-0 bg-gradient-to-b from-orange-50 to-white rounded-full opacity-50 blur-xl scale-90" />

                    <video
                        autoPlay
                        loop
                        muted
                        playsInline
                        className="w-full h-full object-contain z-10 drop-shadow-xl"
                    >
                        <source src="/mascot_animation.mp4" type="video/mp4" />
                        {/* Fallback */}
                        <img src="/mascot_full.png" alt="Mascot Fallback" className="w-full h-full object-contain" />
                    </video>

                    {/* Shadow */}
                    <div className="absolute bottom-4 w-32 h-3 bg-orange-900/10 rounded-full blur-md" />
                </div>

                {/* Login Actions */}
                <div className="w-full flex flex-col gap-3 animate-fade-in-up delay-100">
                    {/* Google Login Button Container */}
                    <div className="relative group">
                        <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
                        <div ref={googleButtonRef} className="w-full flex justify-center h-[50px] relative z-10" />
                    </div>

                    <button
                        onClick={() => handleStart('guest')}
                        className="w-full py-3.5 bg-white border-2 border-gray-100 text-gray-500 rounded-full font-bold hover:bg-gray-50 hover:border-gray-200 active:scale-[0.98] transition-all text-sm flex items-center justify-center gap-2 shadow-sm"
                    >
                        <span>계정 없이 이용하기</span>
                    </button>

                    <p className="text-[10px] text-center text-gray-300 mt-4 leading-relaxed">
                        계속 진행 시 광주-온의 <span className="underline cursor-pointer hover:text-gray-400">이용약관</span> 및 <br />
                        <span className="underline cursor-pointer hover:text-gray-400">개인정보처리방침</span>에 동의하게 됩니다.
                    </p>
                </div>
            </div>
        </div>
    );
};