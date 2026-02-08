import React, { Suspense } from 'react';
import { HistoryScreen } from '../../screens/HistoryScreen';

export default function HistoryPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <HistoryScreen />
        </Suspense>
    );
}
