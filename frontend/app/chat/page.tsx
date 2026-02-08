import React, { Suspense } from 'react';
import { ChatScreen } from "../../screens/ChatScreen";

export default function ChatPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center font-bold">로딩 중...</div>}>
            <ChatScreen />
        </Suspense>
    );
}
