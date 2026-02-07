"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, Calendar, ChevronRight, Share2, ArrowLeft, Bookmark, Wand2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Fix for React 19 type mismatch
const MotionDiv = motion.div as any;
const MotionImg = motion.img as any;

export default function WishlistScreen() {
    const router = useRouter();
    const [wishlist, setWishlist] = useState<any[]>([]);
    const [selectedItem, setSelectedItem] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');

    useEffect(() => {
        const fetchWishlist = async () => {
            const userId = localStorage.getItem('access_token') || localStorage.getItem('temp_user_id');
            if (!userId) {
                setIsLoading(false);
                return;
            }

            try {
                const res = await fetch(`http://localhost:8000/api/journey/wishlist/${userId}`);
                if (res.ok) {
                    const data = await res.json();
                    setWishlist(data.wishlist || []);
                    // 항목이 하나만 있으면 바로 상세로 갈 수도 있지만, 
                    // 사용자가 '목록'을 원했으므로 기본 'list' 모드 유지 (또는 자동 선택 로직)
                }
            } catch (e) {
                console.error("Failed to fetch wishlist", e);
            } finally {
                setIsLoading(false);
            }
        };

        fetchWishlist();
    }, []);

    const handleShare = async (item: any) => {
        const userId = localStorage.getItem('access_token') || localStorage.getItem('temp_user_id') || 'guest';
        const shareUrl = `${window.location.origin}/discovery?shared=${userId}`;

        if (navigator.share) {
            try {
                await navigator.share({
                    title: item.title || '찜한 광주 코스',
                    text: item.description || '내가 찜한 특별한 여정을 확인해보세요.',
                    url: shareUrl
                });
            } catch (e) { console.log(e); }
        } else {
            await navigator.clipboard.writeText(shareUrl);
            alert("공유 링크가 클립보드에 복사되었습니다!");
        }
    };

    const handleCreateMemory = (item: any) => {
        localStorage.setItem('current_course', JSON.stringify(item.spots || []));
        router.push('/timeline?mode=create_memory');
    };

    if (isLoading) {
        return <div className="min-h-screen flex items-center justify-center bg-white"><p className="font-bold text-gray-400">로드 중...</p></div>;
    }

    if (wishlist.length === 0) {
        return (
            <div className="min-h-screen bg-[#FDFBF7] flex flex-col items-center justify-center p-6 text-center">
                <div className="fixed top-4 left-4 z-50">
                    <button onClick={() => router.push('/profile')} className="bg-white/80 backdrop-blur-md p-3 rounded-full shadow-sm text-gray-700 transition-all"><ArrowLeft size={20} /></button>
                </div>
                <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm border border-red-100">
                    <Bookmark size={32} className="text-red-300" />
                </div>
                <h2 className="text-xl font-black text-gray-800 mb-3">찜한 코스가 없어요</h2>
                <p className="text-sm text-gray-400">나만의 여행 계획을 찜해보세요!</p>
            </div>
        );
    }

    const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' });

    // --- 1. 목록 뷰 (List View) ---
    if (viewMode === 'list') {
        return (
            <div className="min-h-screen bg-[#FDFBF7] font-['Inter'] relative pb-32">
                <div className="fixed inset-0 opacity-[0.03] pointer-events-none z-0"
                    style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")` }}
                />
                <header className="flex justify-between items-center px-6 py-5 bg-white shrink-0 border-b border-gray-50 z-[10] relative">
                    <button onClick={() => router.push('/profile')} className="text-gray-400 font-bold text-xs"><ArrowLeft size={18} /></button>
                    <h1 className="text-sm font-black text-gray-800 tracking-tight">찜한 코스 목록</h1>
                    <div className="w-8" />
                </header>

                <div className="max-w-2xl mx-auto px-6 pt-10 pb-20 z-10 relative">
                    <h2 className="text-2xl font-black text-gray-900 mb-8 tracking-tight">내가 찜한 코스들</h2>
                    <div className="space-y-6">
                        {wishlist.map((item, index) => (
                            <MotionDiv
                                key={item.id || index}
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: index * 0.05 }}
                                onClick={() => {
                                    setSelectedItem(item);
                                    setViewMode('detail');
                                }}
                                className="bg-white p-6 rounded-[2.5rem] border border-gray-50 shadow-sm hover:shadow-xl hover:translate-y-[-4px] transition-all cursor-pointer group active:scale-[0.98]"
                            >
                                <div className="flex items-center gap-5">
                                    <div className="w-24 h-24 rounded-3xl overflow-hidden bg-gray-50 shadow-inner">
                                        <img
                                            src={item.spots?.[0]?.imageUrl || item.spots?.[0]?.img || `https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=200&sig=${index}`}
                                            className="w-full h-full object-cover"
                                            alt="cover"
                                        />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1.5">
                                            <span className="text-[10px] font-black text-[#0066FF] uppercase tracking-tighter">COURSE</span>
                                            <span className="text-[10px] text-gray-300">•</span>
                                            <span className="text-[10px] font-bold text-gray-400">{new Date(item.saved_at || Date.now()).toLocaleDateString()}</span>
                                        </div>
                                        <h3 className="text-lg font-black text-gray-900 mb-1 truncate">{item.title || "찜한 코스"}</h3>
                                        <p className="text-xs text-gray-400 font-medium line-clamp-1">{item.spots?.length || 0}개의 장소가 포함되어 있습니다.</p>
                                    </div>
                                    <ChevronRight size={20} className="text-gray-200 group-hover:text-gray-900 group-hover:translate-x-1 transition-all" />
                                </div>
                            </MotionDiv>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // --- 2. 상세 뷰 (Detail View - Photo 2 Style) ---
    const item = selectedItem;
    // If selectedItem is null (shouldn't happen if viewMode is 'detail' and wishlist is not empty, but for safety)
    if (!item) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-white"><p className="font-bold text-gray-400">선택된 코스가 없습니다.</p></div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FDFBF7] font-['Inter'] relative pb-32">
            {/* 배경 텍스처 효과 */}
            <div className="fixed inset-0 opacity-[0.03] pointer-events-none z-0"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")` }}
            />

            {/* Header */}
            <header className="flex justify-between items-center px-6 py-5 bg-white shrink-0 border-b border-gray-50 z-[10] relative">
                <button onClick={() => setViewMode('list')} className="text-gray-400 font-bold text-xs">닫기</button>
                <h1 className="text-sm font-black text-gray-800 tracking-tight">찜한 코스</h1>
                <div className="w-8" />
            </header>

            <div className="max-w-2xl mx-auto px-6 pt-10 pb-20 z-10 relative">
                {/* 상단 타이틀 섹션 */}
                <div className="mb-10">
                    <span className="text-[10px] font-black text-[#0066FF] uppercase tracking-tighter mb-1 block">TRAVEL ALBUM</span>
                    <h1 className="text-3xl font-black text-gray-900 leading-tight mb-3">
                        {item?.title || "최근 여행 기록"}
                    </h1>
                    <div className="flex items-center gap-2 text-xs text-gray-400 font-bold">
                        <Calendar size={12} />
                        <span>{item?.saved_at ? new Date(item.saved_at).toLocaleDateString() : today} · 광주광역시</span>
                    </div>
                </div>

                {/* 상단 액션 카드 (바로가기 / Memory) */}
                <div className="grid grid-cols-2 gap-4 mb-12">
                    <button
                        onClick={() => {
                            localStorage.setItem('current_course', JSON.stringify(item.spots || []));
                            router.push('/map?mode=course_navigator');
                        }}
                        className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-50 flex flex-col items-center justify-center gap-3 active:scale-95 transition-all group"
                    >
                        <div className="w-12 h-12 rounded-[1.25rem] bg-blue-50 flex items-center justify-center text-[#0066FF] group-hover:bg-[#0066FF] group-hover:text-white transition-all shadow-sm">
                            <MapPin size={24} />
                        </div>
                        <div className="text-center">
                            <span className="text-[9px] font-black text-gray-300 block uppercase mb-0.5">JOURNEY</span>
                            <span className="text-base font-black text-gray-800">바로가기</span>
                        </div>
                    </button>

                    <div className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-50 flex flex-col items-center justify-center gap-3 opacity-40">
                        <div className="w-12 h-12 rounded-[1.25rem] bg-red-50 flex items-center justify-center text-red-400 shadow-sm">
                            <Bookmark size={24} />
                        </div>
                        <div className="text-center">
                            <span className="text-[9px] font-black text-gray-300 block uppercase mb-0.5">THEME</span>
                            <span className="text-base font-black text-gray-800">Memory</span>
                        </div>
                    </div>
                </div>

                {/* 기억의 조각들 섹션 */}
                <div className="mb-10">
                    <h3 className="text-xl font-black text-gray-900 mb-6 tracking-tight">기억의 조각들</h3>
                    <div className="space-y-4">
                        {(item?.spots || []).map((spot: any, index: number) => (
                            <MotionDiv
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.05 }}
                                key={index}
                                className="flex items-center gap-4 bg-white p-4 rounded-[2rem] border border-gray-50 shadow-sm group cursor-pointer hover:shadow-md transition-all active:scale-[0.98]"
                                onClick={() => {
                                    localStorage.setItem('current_course', JSON.stringify(item.spots));
                                    router.push(`/map?mode=course_navigator&focus=${index}`);
                                }}
                            >
                                <div className="w-20 h-20 rounded-2xl overflow-hidden shrink-0 bg-gray-50 border border-gray-100 shadow-sm">
                                    <img
                                        src={spot.imageUrl || spot.img || `https://images.unsplash.com/photo-1582234373453-909778434800?w=200&sig=${index}`}
                                        className="w-full h-full object-cover"
                                        alt={spot.name}
                                    />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h4 className="text-base font-black text-gray-800 mb-1 truncate">{spot.name}</h4>
                                    <p className="text-xs text-gray-400 font-medium line-clamp-2 leading-relaxed">
                                        {spot.description || spot.reason || "이 장소에서 보낼 소중한 시간들이 앨범에 담겼습니다."}
                                    </p>
                                </div>
                                <ChevronRight size={18} className="text-gray-200 group-hover:text-gray-900 transition-colors shrink-0" />
                            </MotionDiv>
                        ))}
                    </div>
                </div>

                {/* 하단 공유 배너 */}
                <div className="bg-[#0066FF] p-10 rounded-[2.5rem] text-center relative overflow-hidden group shadow-xl shadow-blue-100">
                    <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 transition-transform group-hover:scale-110"></div>
                    <div className="relative z-10 flex flex-col items-center">
                        <h4 className="text-xl font-black text-white mb-2">기록을 선물해보세요</h4>
                        <p className="text-[11px] text-white/70 font-bold mb-8">당신이 완성한 소중한 여정을<br />친구와 함께 나눌 수 있습니다.</p>
                        <button
                            onClick={() => handleShare(item)}
                            className="w-16 h-16 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-full text-white transition-all active:scale-95 shadow-lg border border-white/20 flex items-center justify-center group-hover:rotate-12"
                        >
                            <Share2 size={28} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Floating Action Button: 추억 앨범 만들기 */}
            <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-40 w-full max-w-2xl px-6">
                <button
                    onClick={() => handleCreateMemory(item)}
                    className="w-full bg-[#FF6B00] text-white py-5 rounded-[2rem] shadow-2xl shadow-orange-200 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-3 font-black text-lg"
                >
                    <Wand2 size={24} className="animate-pulse" />
                    <span>추억 앨범 만들기</span>
                </button>
            </div>
        </div>
    );
}