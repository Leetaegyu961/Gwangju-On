import React from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';

interface LoginModalProps {
    isOpen: boolean;
    onClose: () => void;
    featureName: string; // "찜하기", "타임라인", "초대장" 등
}

const LoginInducementModal: React.FC<LoginModalProps> = ({ isOpen, onClose, featureName }) => {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    if (!isOpen) return null;

    const handleLogin = () => {
        // 현재 페이지 전체 URL을 redirect 파라미터로 전달
        const currentUrl = searchParams.toString()
            ? `${pathname}?${searchParams.toString()}`
            : pathname;
        router.push(`/login?redirect=${encodeURIComponent(currentUrl)}`);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-2xl p-8 max-w-sm w-full mx-4 shadow-2xl transform transition-all scale-100">
                <div className="text-center">
                    {/* 아이콘 영역 */}
                    <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 mb-4">
                        <span className="text-2xl">🔒</span>
                    </div>

                    <h3 className="text-xl font-bold text-gray-900 mb-2">
                        로그인이 필요한 기능이에요
                    </h3>
                    <p className="text-gray-600 mb-6 text-sm leading-relaxed">
                        게스트 모드에서는 <strong>{featureName}</strong> 기능을 이용할 수 없습니다.
                        지금 로그인하고 나만의 여행 기록을 안전하게 보관해보세요!
                    </p>

                    <div className="flex flex-col space-y-3">
                        <button
                            onClick={handleLogin}
                            className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition-colors"
                        >
                            구글로 시작하기
                        </button>
                        <button
                            onClick={onClose}
                            className="w-full text-gray-400 py-2 text-sm hover:text-gray-600 transition-colors"
                        >
                            나중에 할게요
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginInducementModal;
