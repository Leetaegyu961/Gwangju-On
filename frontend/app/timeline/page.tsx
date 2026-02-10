import React, { Suspense } from 'react';
import TimelineScreen from "../../screens/TimelineScreen";

export default function TimelinePage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <TimelineScreen />
        </Suspense>
    );
}
