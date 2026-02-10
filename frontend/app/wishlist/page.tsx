"use client";

import React, { Suspense } from 'react';
import WishlistScreen from '../../screens/WishlistScreen';

export default function WishlistPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <WishlistScreen />
        </Suspense>
    );
}
