import React, { useEffect, useState } from 'react';
import { X, Brain, User, Target, Activity, Database } from 'lucide-react';
import { GeminiService } from '../../services/geminiService';

interface AgentContextDashboardProps {
    isOpen: boolean;
    onClose: () => void;
}

const aiService = new GeminiService();

export const AgentContextDashboard = ({ isOpen, onClose }: AgentContextDashboardProps) => {
    const [context, setContext] = useState<any>(null);
    const [activeTab, setActiveTab] = useState('profile');

    useEffect(() => {
        if (isOpen) {
            aiService.getAgentContext().then(setContext);
        }
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
            <div className="bg-white w-full max-w-lg h-[85vh] rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col relative animate-slide-up">
                {/* Header */}
                <div className="bg-[#0066FF] p-6 text-white flex justify-between items-center shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="bg-white/20 p-2.5 rounded-2xl backdrop-blur-md border border-white/10">
                            <Brain size={24} className="text-white" />
                        </div>
                        <div>
                            <h2 className="font-black text-lg tracking-tight">Agent Context</h2>
                            <p className="text-xs text-blue-100 font-medium">실시간 데이터 처리 현황</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-full transition-colors active:scale-90">
                        <X size={24} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-100 p-2 gap-2 overflow-x-auto hide-scrollbar shrink-0 bg-white">
                    {[
                        { id: 'profile', icon: User, label: '프로필' },
                        { id: 'intent', icon: Target, label: '여행 의도' },
                        { id: 'activity', icon: Activity, label: '활동 로그' },
                        { id: 'raw', icon: Database, label: 'Raw Data' },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-3 rounded-2xl text-sm font-bold transition-all whitespace-nowrap ${
                                activeTab === tab.id 
                                ? 'bg-blue-50 text-[#0066FF] shadow-sm ring-1 ring-blue-100' 
                                : 'text-gray-400 hover:bg-gray-50'
                            }`}
                        >
                            <tab.icon size={16} />
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 bg-[#F8FAFC]">
                    {context ? (
                        <div className="space-y-6 pb-10">
                            {activeTab === 'profile' && (
                                <div className="space-y-4 animate-fade-in">
                                    <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-100">
                                        <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 bg-[#0066FF] rounded-full" />
                                            선호도 가중치 (Weights)
                                        </h3>
                                        <div className="flex flex-wrap gap-2">
                                            {Object.entries(context.profile?.preference_weights?.themes || {}).map(([k, v]: any) => (
                                                <div key={k} className="flex items-center gap-2 bg-blue-50 px-4 py-2 rounded-xl border border-blue-100">
                                                    <span className="text-xs font-bold text-gray-600">{k}</span>
                                                    <span className="text-xs font-black text-[#0066FF] bg-white px-1.5 py-0.5 rounded-md shadow-sm">{v.toFixed(1)}</span>
                                                </div>
                                            ))}
                                            {Object.keys(context.profile?.preference_weights?.themes || {}).length === 0 && (
                                                <p className="text-sm text-gray-400 font-medium">아직 수집된 취향 데이터가 없습니다.</p>
                                            )}
                                        </div>
                                    </div>
                                    <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-100">
                                        <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 bg-[#0066FF] rounded-full" />
                                            설정 정보
                                        </h3>
                                        <div className="flex justify-between items-center p-3 bg-gray-50 rounded-2xl">
                                            <span className="text-sm font-bold text-gray-600">가격 민감도</span>
                                            <span className="text-sm font-black text-[#0066FF]">{context.profile?.preference_weights?.price_sensitivity || '0.5'}</span>
                                        </div>
                                        <div className="mt-2 flex justify-between items-center p-3 bg-gray-50 rounded-2xl">
                                            <span className="text-sm font-bold text-gray-600">마지막 업데이트</span>
                                            <span className="text-xs font-medium text-gray-400">
                                                {context.profile?.last_updated ? new Date(context.profile.last_updated).toLocaleString() : '-'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'intent' && (
                                <div className="space-y-4 animate-fade-in">
                                    <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-100">
                                        <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 bg-[#0066FF] rounded-full" />
                                            현재 세션 (Short-term Memory)
                                        </h3>
                                        <div className="space-y-4">
                                            <InfoRow label="지역" value={context.active_session?.intent_context?.survey_data?.region} />
                                            <InfoRow label="동행" value={context.active_session?.intent_context?.survey_data?.companions?.join(', ')} />
                                            <InfoRow label="테마" value={context.active_session?.intent_context?.survey_data?.themes?.join(', ')} />
                                            <InfoRow label="예산 범위" value={context.active_session?.intent_context?.survey_data?.budget?.join(' ~ ') + '만원'} />
                                            <InfoRow label="세션 상태" value={context.active_session?.status} />
                                        </div>
                                    </div>

                                    <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-100">
                                        <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-5 flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 bg-[#0066FF] rounded-full" />
                                            사용자 프롬프트 기록 (User Prompts)
                                        </h3>
                                        <div className="space-y-3 max-h-[200px] overflow-y-auto custom-scrollbar pr-2">
                                            {context.active_session?.intent_context?.chat_history?.length > 0 ? (
                                                context.active_session.intent_context.chat_history
                                                    .filter((msg: any) => msg.role === 'user')
                                                    .map((msg: any, i: number) => (
                                                        <div key={i} className="bg-gray-50 p-3 rounded-xl border border-gray-100">
                                                            <div className="flex justify-between mb-1">
                                                                <span className="text-[10px] font-black text-gray-400 uppercase">USER</span>
                                                                <span className="text-[10px] text-gray-300">#{i + 1}</span>
                                                            </div>
                                                            <p className="text-xs font-bold text-gray-700 leading-relaxed">
                                                                {msg.content || msg.text || msg.message || '(No content)'}
                                                            </p>
                                                        </div>
                                                    ))
                                            ) : (
                                                <div className="text-center py-5">
                                                    <p className="text-sm text-gray-400 font-medium">채팅 기록이 없습니다.</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'activity' && (
                                <div className="space-y-3 animate-fade-in">
                                    {context.recent_logs?.length > 0 ? context.recent_logs.map((log: any, i: number) => (
                                        <div key={i} className="bg-white p-5 rounded-[1.5rem] shadow-sm border border-gray-100 flex items-start gap-4">
                                            <div className={`p-3 rounded-2xl shrink-0 shadow-sm ${
                                                log.action === 'PICK' ? 'bg-blue-100 text-blue-600' : 
                                                log.action === 'REJECT' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
                                            }`}>
                                                <Activity size={18} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex justify-between items-center mb-1">
                                                    <p className="text-xs font-black text-gray-800 uppercase tracking-wide">{log.action}</p>
                                                    <span className="text-[10px] text-gray-400 font-medium">{new Date(log.timestamp).toLocaleTimeString()}</span>
                                                </div>
                                                <p className="text-xs text-gray-500 font-bold truncate mb-2">{log.targetPlaceId}</p>
                                                <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
                                                     <pre className="text-[10px] text-gray-400 overflow-x-auto font-mono custom-scrollbar">
                                                        {JSON.stringify(log.context_snapshot || {}, null, 2)}
                                                    </pre>
                                                </div>
                                            </div>
                                        </div>
                                    )) : (
                                        <div className="text-center py-10 text-gray-400 font-medium">최근 활동 기록이 없습니다.</div>
                                    )}
                                </div>
                            )}

                            {activeTab === 'raw' && (
                                <div className="bg-[#1e293b] p-5 rounded-[2rem] shadow-inner h-full min-h-[400px]">
                                    <pre className="text-green-400 text-[10px] overflow-auto h-full font-mono custom-scrollbar leading-relaxed">
                                        {JSON.stringify(context, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center gap-4">
                            <div className="animate-spin rounded-full h-10 w-10 border-4 border-gray-100 border-t-[#0066FF]"></div>
                            <p className="text-sm font-bold text-gray-400 animate-pulse">데이터 로딩 중...</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const InfoRow = ({ label, value }: { label: string, value: any }) => (
    <div className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-xl transition-colors">
        <span className="text-xs font-bold text-gray-400">{label}</span>
        <span className="text-sm font-black text-gray-700 text-right max-w-[60%] truncate">{value || '-'}</span>
    </div>
);
