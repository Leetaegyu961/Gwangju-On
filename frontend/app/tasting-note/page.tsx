"use client";

import React, { Suspense } from 'react';
import { TastingNoteScreen } from '../../screens/TastingNoteScreen';

export default function TastingNotePage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <TastingNoteScreen />
        </Suspense>
    );
}
