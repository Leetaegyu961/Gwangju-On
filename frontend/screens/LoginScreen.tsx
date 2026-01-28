
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
            try {
                // Check for Client ID
                const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "117313124086-rc4e20pfeo597aqolshtspeunsh3hmh3.apps.googleusercontent.com";

                // Reset Google One Tap cooldown (for dev/testing reliability)
                document.cookie = `g_state=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT`;

                (window as any).google.accounts.id.initialize({
                    client_id: clientId,
                    use_fedcm_for_prompt: true,
                    callback: async (response: any) => {
                        console.log("Google Login Response:", response);

                        // 백엔드로 토큰 전송하여 검증 및 로그인 처리
                        try {
                            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/auth/google`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ id_token: response.credential })
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
                    }
                });
                (window as any).google.accounts.id.prompt((notification: any) => {
                    if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                        console.log("One Tap skipped or not displayed:", notification);
                    }
                });
            } catch (error) {
                console.error("GSI Initialization Error:", error);
                alert("구글 로그인 초기화 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            }
        } else {
            console.warn("Google Script not loaded yet. Retrying in 500ms...");
            setTimeout(() => handleGoogleLogin(), 500);
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
            <div className="flex flex-col items-center mb-10 animate-fade-in">
                <div className="w-64 h-64 mb-6 flex items-center justify-center relative">
                    {/* Replicating the mascot mountain character from Image 0 */}
                    <img
                        src="https://img.freepik.com/free-vector/cute-mountain-character-illustration_23-2148766126.jpg?w=740"
                        className="w-full h-full object-contain"
                        alt="ONui Mascot"
                    />
                    {/* Optional: Add a subtle shadow under the mascot */}
                    <div className="absolute bottom-4 w-32 h-4 bg-gray-100 rounded-full blur-md -z-10" />
                </div>
                <h1 className="text-2xl font-black text-gray-900 text-center leading-tight mb-2">
                    AI 큐레이터와 함께하는<br />특별한 광주 여행
                </h1>
                <p className="text-gray-400 text-sm font-medium">나만의 맞춤형 여행 코스를 발견해보세요</p>
            </div>

            {/* Action Area (Image 0) */}
            <div className="w-full max-w-[340px] flex flex-col items-center gap-4 animate-fade-in" style={{ animationDelay: '0.2s' }}>
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
                    className="w-full py-4 bg-gray-100 text-gray-600 rounded-[2rem] font-bold hover:bg-gray-200 active:scale-[0.98] transition-all"
                >
                    계정 없이 시작하기
                </button>
            </div>

            {/* Invisible Spacer for vertical alignment matching Image 0 */}
            <div className="h-20" />
        </div>
    );
};