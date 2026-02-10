import React, { Suspense } from 'react';
import { LoginScreen } from "../../screens/LoginScreen";

export default function LoginPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <LoginScreen />
        </Suspense>
    );
}
