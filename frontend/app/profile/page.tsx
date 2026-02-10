import React, { Suspense } from 'react';
import { MyPage } from "../../screens/MyPage";

export default function ProfilePage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <MyPage />
        </Suspense>
    );
}
