import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Share2, Map as MapIcon, Heart, Calendar, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import LoginInducementModal from '../../components/auth/LoginModal';

export const SummarySequence = ({ pickedPlaces, aiSummary }: { pickedPlaces: any[], aiSummary?: string }) => {
    const router = useRouter();
    const [todayStr] = useState(new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }));
    const [isWishlisted, setIsWishlisted] = useState(false);

    // [v4.5] Guest Gate State
    const [showLoginModal, setShowLoginModal] = useState(false);
    const [modalFeature, setModalFeature] = useState("");

    const checkIsGuest = () => !localStorage.getItem('access_token');

    const handleSaveWishlist = async () => {
        if (isWishlisted) return;

        if (checkIsGuest()) {
            setModalFeature("여정 테마 찜하기(기록)");
            setShowLoginModal(true);
            return;
        }

        try {
            const userId = localStorage.getItem('access_token') || localStorage.getItem('temp_user_id') || 'guest';

            // MapView와 통신 규격을 맞추기 위해 모든 필드 포함
            const processedPlaces = pickedPlaces.map(p => ({
                id: p.id,
                name: p.name,
                lat: p.lat,
                lng: p.lng,
                description: p.description || p.reason || '',
                imageUrl: p.imageUrl,
                tags: p.tags || []
            }));

            await fetch('http://localhost:8000/api/journey/save-wishlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userId,
                    courseData: { pickedPlaces: processedPlaces, aiSummary }
                })
            });
            setIsWishlisted(true);
            alert("코스가 마이페이지 찜 목록에 저장되었습니다!");
        } catch (e) {
            console.error(e);
        }
    };

    const handleShare = async () => {
        if (checkIsGuest()) {
            setModalFeature("여행 초대장 생성 및 공유");
            setShowLoginModal(true);
            return;
        }

        const userId = localStorage.getItem('temp_user_id') || localStorage.getItem('access_token') || 'guest';
        const shareUrl = `${window.location.origin}/discovery?shared=${userId}`;

        if (navigator.share) {
            try {
                await navigator.share({
                    title: '최고의 광주 여행 기록',
                    text: aiSummary || '당신을 위한 특별한 여행 코스입니다.',
                    url: shareUrl
                });
            } catch (e) { console.log(e); }
        } else {
            await navigator.clipboard.writeText(shareUrl);
            alert("공유 링크가 클립보드에 복사되었습니다!");
        }
    };


    const handleApplyCourseToSession = async () => {
        try {
            const userId = localStorage.getItem('access_token') || localStorage.getItem('temp_user_id') || 'guest';

            // 1. 세션에 코스 주입 ( album_data 포인트로 저장 )
            // MapView가 album_data를 인식하도록 형식을 맞춤
            const mapPoints = pickedPlaces.map((p, i) => ({
                id: p.id || i.toString(),
                name: p.name,
                lat: p.lat,
                lng: p.lng,
                desc: p.description || p.reason || '',
                tags: p.tags || [],
                transport: '이동',
                img: p.imageUrl
            }));

            // 로컬 스토리지 업데이트 (즉시 반영용)
            localStorage.setItem('current_course', JSON.stringify(mapPoints));

            // 백엔드 세션 업데이트
            await fetch(`http://localhost:8000/api/session/apply-invitation/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    album_data: mapPoints
                })
            });

            // 2. 지도로 이동
            router.push('/map?mode=course_navigator');
        } catch (e) {
            console.error("Failed to apply course to session", e);
            // 에러 시에도 최소한 로컬 스토리지 기반으로 이동 시도
            router.push('/map');
        }
    };

    const handleCloseInternal = () => {
        // 초대장 완료 후 닫기 시, 로그인 여부에 따른 분기
        const isLoggedIn = !!localStorage.getItem('access_token');
        if (isLoggedIn) {
            router.push('/map');
        } else {
            router.push('/survey');
        }
    };

    return (
        <div className="fixed inset-0 z-[400] bg-[#F8FAFC] flex flex-col font-['Inter']">
            {/* Header */}
            <header className="flex justify-between items-center px-6 py-5 bg-white shrink-0 border-b border-gray-50 z-[10]">
                <button onClick={handleCloseInternal} className="text-gray-400 font-bold text-sm">닫기</button>
                <h1 className="text-lg font-black text-gray-800 tracking-tight">나의 여행 앨범</h1>
                <div className="w-8" />
            </header>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto hide-scrollbar pb-32">

                {/* 1. Header Info (Compact version) */}
                <section className="px-8 pt-8 pb-6">
                    <p className="text-[11px] font-black text-[#0066FF] uppercase tracking-[0.2em] mb-2">TRAVEL ALBUM</p>
                    <h2 className="text-3xl font-black text-gray-900 leading-tight tracking-tight">
                        광주에서의<br />소중한 기록들
                    </h2>
                    <div className="flex items-center gap-2 mt-4 text-gray-400">
                        <Calendar size={14} />
                        <span className="text-xs font-bold">{todayStr} · 광주광역시</span>
                    </div>
                </section>

                {/* 2. Stat Cards */}
                <section className="px-6 grid grid-cols-2 gap-4 mb-10">
                    <button
                        onClick={handleApplyCourseToSession}
                        className="bg-white p-6 rounded-[2rem] shadow-sm border border-gray-50 flex flex-col items-center text-center hover:bg-gray-50 transition-colors active:scale-95 group"
                    >
                        <div className="w-12 h-12 bg-blue-50 text-blue-500 rounded-2xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <MapIcon size={24} />
                        </div>
                        <span className="text-[10px] font-black text-gray-300 uppercase tracking-widest mb-1">JOURNEY</span>
                        <p className="text-xl font-black text-gray-900">바로가기</p>
                    </button>
                    <button
                        onClick={handleSaveWishlist}
                        className={`p-6 rounded-[2rem] shadow-sm border transition-all flex flex-col items-center text-center ${isWishlisted ? 'bg-pink-50 border-pink-100' : 'bg-white border-gray-50'
                            }`}
                    >
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-3 ${isWishlisted ? 'bg-pink-100 text-pink-500' : 'bg-gray-50 text-gray-300'
                            }`}>
                            <Heart size={24} fill={isWishlisted ? "currentColor" : "none"} />
                        </div>
                        <span className="text-[10px] font-black text-gray-300 uppercase tracking-widest mb-1">THEME</span>
                        <p className={`text-xl font-black ${isWishlisted ? 'text-pink-500' : 'text-gray-900'}`}>
                            {isWishlisted ? "Saved" : "Memory"}
                        </p>
                    </button>
                </section>

                {/* 3. Visited List (3rd style: 1/5 Thumbnail + Right Text) */}
                <section className="px-6 mb-12">
                    <h3 className="text-xl font-black text-gray-900 mb-6 px-2 tracking-tight">기억의 조각들</h3>
                    <div className="flex flex-col gap-3">
                        {pickedPlaces.map((place, index) => (
                            <div key={`${place.id}-${index}`} className="w-full bg-white rounded-[2rem] p-4 shadow-sm border border-gray-50 flex items-center gap-4 active:scale-[0.98] transition-all">
                                {/* 캡처본 1/5 썸네일 스타일 */}
                                <div className="w-24 h-24 shrink-0 rounded-2xl overflow-hidden relative shadow-sm">
                                    <img src={place.imageUrl} className="w-full h-full object-cover" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h4 className="text-base font-black text-gray-900 truncate mb-1">{place.name}</h4>
                                    <p className="text-xs text-gray-400 font-medium leading-relaxed line-clamp-2">
                                        {place.description || "이 장소에서 보낸 소중한 시간들이 앨범에 담겼습니다."}
                                    </p>
                                </div>
                                <ChevronRight size={16} className="text-gray-200 ml-1" />
                            </div>
                        ))}
                    </div>
                </section>

                {/* 4. Share Banner */}
                <section className="px-6 mb-10">
                    <div className="bg-[#0066FF] rounded-[2.5rem] p-8 text-center shadow-xl shadow-blue-100 text-white relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-10 -mt-10" />
                        <h3 className="text-xl font-black mb-2 relative z-10">기록을 선물해보세요</h3>
                        <p className="text-[11px] font-bold text-white/70 mb-6 relative z-10">
                            당신이 완성한 소중한 여정을<br />친구와 함께 나눌 수 있습니다.
                        </p>
                        <button
                            onClick={handleShare}
                            className="bg-white/20 hover:bg-white/30 transition-all p-4 rounded-2xl mx-auto flex items-center justify-center relative z-10"
                        >
                            <Share2 size={24} />
                        </button>
                    </div>
                </section>

            </div>

            {/* Global Nav overlap safe area is handled by pb-32 above */}
            <LoginInducementModal
                isOpen={showLoginModal}
                onClose={() => setShowLoginModal(false)}
                featureName={modalFeature}
            />
        </div>
    );
};
