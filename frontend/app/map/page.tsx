import React, { Suspense } from 'react';
import { MapView } from "../../screens/MapView";

export default function MapPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <MapView />
        </Suspense>
    );
}
