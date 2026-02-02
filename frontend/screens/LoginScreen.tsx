
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
                        auto_select: false,
                        use_fedcm_for_prompt: false,
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
        <div className="min-h-screen bg-white flex flex-col items-center justify-center p-6 font-['Inter'] relative overflow-hidden">
            {/* Video Background */}
            <video
                autoPlay
                loop
                muted
                playsInline
                className="absolute inset-0 w-full h-full object-cover z-0"
            >
                <source src="/mascot_animation.mp4" type="video/mp4" />
            </video>

            {/* Overlay */}
            <div className="absolute inset-0 bg-black/30 z-0" />

            {/* Content Area */}
            <div className="relative z-10 w-full flex flex-col items-center">
                <div className="flex flex-col items-center mb-16 animate-fade-in">
                    <h1 className="text-3xl font-black text-white text-center leading-tight mb-3 drop-shadow-lg">
                        AI 큐레이터와 함께하는<br />특별한 광주 여행
                    </h1>
                    <p className="text-white/90 text-sm font-medium drop-shadow-md">나만의 맞춤형 여행 코스를 발견해보세요</p>
                </div>

                {/* Action Area */}
                <div className="w-full max-w-[340px] flex flex-col items-center gap-4 animate-fade-in" style={{ animationDelay: '0.2s' }}>
                    {/* Google Login Button Container */}
                    <div ref={googleButtonRef} className="w-full flex justify-center h-[56px]" />

                    <button
                        onClick={() => handleStart('guest')}
                        className="w-full py-4 bg-white/20 backdrop-blur-md text-white border border-white/30 rounded-full font-bold hover:bg-white/30 active:scale-[0.98] transition-all shadow-lg"
                    >
                        계정 없이 시작하기
                    </button>
                </div>
            </div>

            {/* Footer / Copyright */}
            <div className="absolute bottom-8 text-white/50 text-[10px] z-10">
                © 2024 Gwangju-On. All rights reserved.
            </div>
        </div>
    );
};