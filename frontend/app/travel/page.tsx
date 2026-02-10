import React, { Suspense } from 'react';
import TravelView from '../../screens/TravelView';

export default function TravelPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-[#0066FF] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-bold text-gray-500">여행 준비 중...</span>
        </div>
      </div>
    }>
      <TravelView />
    </Suspense>
  );
}
