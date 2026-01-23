
import React from 'react';
import { ProfileSetupScreen } from "../../screens/ProfileSetupScreen";

export default function OnboardingPage() {
    return (
        <React.Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <ProfileSetupScreen />
        </React.Suspense>
    );
}
