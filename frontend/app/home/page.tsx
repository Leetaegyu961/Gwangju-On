import React, { Suspense } from 'react';
import { HomeScreen } from "../../screens/HomeScreen";

export default function HomePage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <HomeScreen />
        </Suspense>
    );
}
