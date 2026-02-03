import React from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, LogIn, Sparkles } from 'lucide-react';

interface GuestSettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onLogout: () => void;
}

const GuestSettingsModal: React.FC<GuestSettingsModalProps> = ({ isOpen, onClose, onLogout }) => {
    const router = useRouter();

    if (!isOpen) return null;

    const handleLogin = () => {
        router.push('/login');
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm animate-fade-in" onClick={onClose}>
            <div className="bg-white rounded-[2rem] p-8 max-w-sm w-full mx-4 shadow-2xl transform transition-all scale-100" onClick={e => e.stopPropagation()}>
                <div className="text-center">
                    <div className="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-gradient-to-tr from-blue-100 to-purple-50 mb-6 shadow-inner">
                        <Sparkles className="text-blue-500" size={32} />
                    </div>

                    <h3 className="text-2xl font-black text-gray-900 mb-3 tracking-tight">
                        여행 기록을 보관하세요!
                    </h3>
                    <p className="text-gray-500 mb-8 text-sm leading-relaxed font-medium">
                        게스트 계정은 로그아웃 시<br />
                        모든 여행 기록이 삭제됩니다.<br />
                        <strong className="text-blue-600">로그인하고 추억을 영구 소장하세요.</strong>
                    </p>

                    <div className="space-y-3">
                        <button
                            onClick={handleLogin}
                            className="w-full bg-[#0066FF] text-white py-4 rounded-xl font-bold text-lg hover:bg-blue-600 active:scale-95 transition-all shadow-lg shadow-blue-200 flex items-center justify-center gap-2"
                        >
                            <LogIn size={20} />
                            구글로 시작하기
                        </button>
                        <button
                            onClick={onLogout}
                            className="w-full bg-gray-50 text-gray-400 py-4 rounded-xl font-bold text-sm hover:bg-gray-100 hover:text-red-500 transition-colors flex items-center justify-center gap-2"
                        >
                            <LogOut size={16} />
                            삭제하고 로그아웃
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default GuestSettingsModal;
