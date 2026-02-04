import { Suspense } from 'react';
import TimelineScreen from "../../screens/TimelineScreen";

export default function TimelinePage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center font-bold text-gray-400">Loading...</div>}>
            <TimelineScreen />
        </Suspense>
    );
}
