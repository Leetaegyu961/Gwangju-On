import React, { useState } from 'react';
import { LogOut, Save, User, Loader2 } from 'lucide-react';

interface UserSettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onLogout: () => void;
    userId: string;
    initialAge?: string;
    initialGender?: string;
    onProfileUpdate: (age: string, gender: string) => void;
}

const UserSettingsModal: React.FC<UserSettingsModalProps> = ({
    isOpen, onClose, onLogout, userId, initialAge, initialGender, onProfileUpdate
}) => {
    const [age, setAge] = useState(initialAge || '');
    const [gender, setGender] = useState(initialGender || '');
    const [isSaving, setIsSaving] = useState(false);

    if (!isOpen) return null;

    const handleSave = async () => {
        if (!age || !gender) return;
        setIsSaving(true);
        try {
            // API Call
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/user/profile`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId, age, gender })
            });

            if (response.ok) {
                onProfileUpdate(age, gender);
                onClose();
            } else {
                alert('프로필 업데이트 실패');
            }
        } catch (error) {
            console.error(error);
            alert('서버 오류가 발생했습니다.');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm animate-fade-in" onClick={onClose}>
            <div className="bg-white rounded-[2rem] p-8 max-w-sm w-full mx-4 shadow-2xl transform transition-all scale-100" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-8">
                    <h3 className="text-2xl font-black text-gray-900 tracking-tight">내 정보 수정</h3>
                    <div className="p-2 bg-gray-50 rounded-full">
                        <User className="text-gray-400" size={24} />
                    </div>
                </div>

                <div className="space-y-6 mb-8">
                    {/* Age Selection */}
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-widest">연령대</label>
                        <div className="grid grid-cols-3 gap-2">
                            {['20대', '30대', '40대', '50대', '60대+'].map((a) => (
                                <button
                                    key={a}
                                    onClick={() => setAge(a)}
                                    className={`py-2 rounded-xl text-sm font-bold transition-all ${age === a
                                            ? 'bg-[#0066FF] text-white shadow-md shadow-blue-200'
                                            : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                                        }`}
                                >
                                    {a}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Gender Selection */}
                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-widest">성별</label>
                        <div className="flex gap-2">
                            {['남성', '여성'].map((g) => (
                                <button
                                    key={g}
                                    onClick={() => setGender(g)}
                                    className={`flex-1 py-2 rounded-xl text-sm font-bold transition-all ${gender === g
                                            ? 'bg-[#0066FF] text-white shadow-md shadow-blue-200'
                                            : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                                        }`}
                                >
                                    {g}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="space-y-3">
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="w-full bg-[#0066FF] text-white py-4 rounded-xl font-bold text-lg hover:bg-blue-600 active:scale-95 transition-all shadow-lg shadow-blue-200 flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        {isSaving ? <Loader2 className="animate-spin" /> : <Save size={20} />}
                        변경사항 저장
                    </button>
                    <button
                        onClick={onLogout}
                        className="w-full bg-white border-2 border-red-50 text-red-400 py-3.5 rounded-xl font-bold text-sm hover:bg-red-50 hover:text-red-500 transition-colors flex items-center justify-center gap-2"
                    >
                        <LogOut size={16} />
                        로그아웃
                    </button>
                </div>
            </div>
        </div>
    );
};

export default UserSettingsModal;
