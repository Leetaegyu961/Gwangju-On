import React, { Suspense } from 'react';
import { SurveyScreen } from "../../screens/SurveyScreen";

export default function SurveyPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <SurveyScreen />
        </Suspense>
    );
}
