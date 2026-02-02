"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Camera, Calendar, MapPin, CheckCircle2, X, Download, Wand2, ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, Plus, FolderArchive, Images } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import html2canvas from 'html2canvas';
import Script from 'next/script';

// 앨범 데이터 타입 정의
interface Album {
    id: string;
    title: string;
    date: string;
    location: string;
    coverImg?: string;
    description: string;
    spots: any[]; // 코스 데이터
    isNew?: boolean; // 최근 생성된 코스 여부
}

export default function TimelineScreen() {
    const router = useRouter();

    // 뷰 모드: 'list' (앨범 목록) | 'detail' (상세 타임라인)
    const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');
    const [course, setCourse] = useState<any[]>([]);

    const [albums, setAlbums] = useState<Album[]>([]);
    const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);

    // 상세 뷰 상태 (기존 로직 유지)
    const [photos, setPhotos] = useState<{ [key: number]: string }>({});
    const [isCardModalOpen, setIsCardModalOpen] = useState(false);
    const [currentSlide, setCurrentSlide] = useState(0); // Album Slide State
    const cardRef = useRef<HTMLDivElement>(null);
    const hiddenSlidesRef = useRef<HTMLDivElement>(null); // Ref for hidden all-slides
    const [isGenerating, setIsGenerating] = useState(false);

    // [New] Tmap 미니맵 관련 상태
    const miniMapRef = useRef<HTMLDivElement>(null);
    const miniMapInstance = useRef<any>(null);
    const [isMiniMapReady, setIsMiniMapReady] = useState(false);
    // [New] 다운로드 중인지 여부 (True면 Tmap 대신 SVG 지도를 렌더링)
    const [isDownloading, setIsDownloading] = useState(false);

    useEffect(() => {
        // 1. 저장된 코스(최근 코스) 불러오기
        const stored = localStorage.getItem('current_course');
        const currentCourseSpots = stored ? JSON.parse(stored) : [];
        const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\./g, '.');

        // 2. 더미 데이터 (지난 여행) 생성 - 제거됨
        const pastAlbums: Album[] = [];

        // 3. 현재 코스가 있다면 최상단에 추가
        if (currentCourseSpots.length > 0) {
            const currentAlbum: Album = {
                id: 'current',
                title: '광주에서 보낸 오후',
                date: today,
                location: '광주 동구', // 임시 위치
                description: '#혼행 #힐링',
                spots: currentCourseSpots,
                isNew: true
            };
            setAlbums([currentAlbum, ...pastAlbums]);
        } else {
            setAlbums(pastAlbums);
        }
    }, []);

    // [New] Tmap 초기화 함수 (미니맵용)
    const initMiniMap = () => {
        if (!miniMapRef.current || !(window as any).Tmapv3 || miniMapInstance.current) return;

        console.log("🗺️ [Timeline] Initializing MiniMap...");
        const Tmapv3 = (window as any).Tmapv3;

        // 1. 초기 중심 좌표 계산 (첫 번째 장소)
        let centerLat = 35.1595;
        let centerLng = 126.8526;

        // 현재 보여지는 코스 데이터 가져오기
        const currentCourse = selectedAlbum ? selectedAlbum.spots : (albums.length > 0 ? albums[0].spots : []);

        if (currentCourse.length > 0) {
            centerLat = parseFloat(currentCourse[0].lat);
            centerLng = parseFloat(currentCourse[0].lng);
        }

        // 2. 지도 생성 (줌 컨트롤 등 불필요한 UI 제거)
        miniMapInstance.current = new Tmapv3.Map(miniMapRef.current, {
            center: new Tmapv3.LatLng(centerLat, centerLng),
            width: "100%",
            height: "100%",
            zoom: 14,
            zoomControl: false,
            scrollwheel: false, // 스크롤 줌 방지
            draggable: false,   // 드래그 방지 (정적 지도처럼 보이게)
        });

        // 3. 마커 및 경로 그리기
        const bounds = new Tmapv3.LatLngBounds();
        const path: any[] = [];

        currentCourse.forEach((spot: any, idx: number) => {
            const lat = parseFloat(spot.lat);
            const lng = parseFloat(spot.lng);
            const position = new Tmapv3.LatLng(lat, lng);

            path.push(position);
            bounds.extend(position);

            // 심플한 숫자 마커
            const markerContent = `<div style="background:#FF6B00; color:white; width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:10px; border:2px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.2);">${idx + 1}</div>`;

            new Tmapv3.Marker({
                position: position,
                map: miniMapInstance.current,
                iconHTML: markerContent
            });
        });

        // 경로 선 그리기
        if (path.length > 1) {
            new Tmapv3.Polyline({
                path: path,
                strokeColor: "#FF6B00",
                strokeWeight: 3,
                map: miniMapInstance.current,
                strokeStyle: "dashed" // 점선 스타일
            });
        }

        // 4. 지도 영역 맞춤
        setTimeout(() => {
            if (miniMapInstance.current) {
                miniMapInstance.current.fitBounds(bounds, { top: 20, bottom: 20, left: 20, right: 20 });
            }
        }, 100);

        setIsMiniMapReady(true);
    };

    // Tmap 로드 감지 및 초기화 (슬라이드가 'Ending'일 때 등 트리거)
    useEffect(() => {
        // 엔딩 슬라이드가 아니거나 다운로드 중이면 중단
        if (currentSlide <= course.length || isDownloading) return;

        // 다운로드가 끝나고 돌아왔을 때, 기존 인스턴스 초기화 (DOM이 새로 생겼으므로)
        if (miniMapInstance.current) {
            miniMapInstance.current = null;
            setIsMiniMapReady(false);
        }

        // 지도 초기화 시도
        const checkMap = setInterval(() => {
            // miniMapRef가 존재하고, Tmap 스크립트가 로드되었으며, 인스턴스가 없을 때
            if (miniMapRef.current && (window as any).Tmapv3 && !miniMapInstance.current) {
                initMiniMap();
                clearInterval(checkMap);
            }
        }, 500);
        return () => clearInterval(checkMap);
    }, [currentSlide, isDownloading]); // isDownloading이 false가 되면 다시 실행됨

    const handleImageUpload = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setPhotos(prev => ({
                    ...prev,
                    [index]: reader.result as string
                }));
            };
            reader.readAsDataURL(file);
        }
    };

    // 사진 삭제 (취소) 기능
    const handleImageDelete = (index: number, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation(); // 라벨(파일선택) 클릭 방지
        setPhotos(prev => {
            const newPhotos = { ...prev };
            delete newPhotos[index];
            return newPhotos;
        });
    };

    // Save Current Slide Logic
    const handleDownloadCard = async () => {
        if (!cardRef.current) return;
        setIsGenerating(true);

        setIsDownloading(true); // 캡처 모드 시작 (Tmap -> SVG 전환)

        try {
            // DOM이 SVG로 전환될 때까지 충분히 대기
            await new Promise(resolve => setTimeout(resolve, 800));
            // 전체 카드 캡처
            const capturedCanvas = await html2canvas(cardRef.current, {
                scale: 2,
                backgroundColor: '#FDFBF7',
                useCORS: true,
                logging: false,
            });

            const image = capturedCanvas.toDataURL("image/png");

            // 파일명 생성
            const todayStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
            const fileName = `GwangjuOn_Trip_${todayStr}.png`;

            const link = document.createElement("a");
            link.href = image;
            link.download = fileName;
            link.click();
        } catch (err) {
            console.error("Failed to generate image", err);
            alert("이미지 생성에 실패했습니다.");
        } finally {
            setIsDownloading(false); // 캡처 모드 종료 (SVG -> Tmap 복귀)
            setIsGenerating(false);
        }
    };


    // Save All Slides as Images (Sequentially)
    const handleDownloadAll = async () => {
        if (isGenerating || !cardRef.current) return;
        setIsGenerating(true);
        const originalSlide = currentSlide;

        try {
            // Total slides: Cover (0) + Spots (course.length) + Ending (1)
            const totalSlides = course.length + 2;

            for (let i = 0; i < totalSlides; i++) {
                // 1. Switch Slide
                setCurrentSlide(i);

                // 2. Wait for animation/rendering (Transition duration is 0.3s, so wait a bit more)
                await new Promise(resolve => setTimeout(resolve, 800));

                // 3. Capture
                if (cardRef.current) {
                    const canvas = await html2canvas(cardRef.current, {
                        scale: 2,
                        backgroundColor: '#FDFBF7',
                        useCORS: true,
                        logging: false,
                        allowTaint: true, // Allow cross-origin images if configured
                    });

                    const image = canvas.toDataURL("image/png");
                    const link = document.createElement("a");
                    link.href = image;
                    // File Name
                    const fileName = i === 0 ? '00_cover.png' : i === totalSlides - 1 ? '99_ending.png' : `0${i}_spot.png`;
                    link.download = `gwangju-memory-${fileName}`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
            }

            // Restore original slide after done
            setCurrentSlide(originalSlide);
            alert("모든 페이지가 저장되었습니다!");

        } catch (err) {
            console.error("Failed to download images", err);
            alert("저장 중 오류가 발생했습니다.");
        } finally {
            setIsGenerating(false);
        }
    };


    const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\./g, '.');

    // 앨범 클릭 핸들러
    const handleAlbumClick = (album: Album) => {
        setSelectedAlbum(album);
        // 상세 뷰 호환성을 위해 course 상태 업데이트
        setCourse(album.spots);
        setPhotos({});
        setViewMode('detail');
    };

    // 기본 이미지 (사진 없을 때)
    const placeholders = [
        "/placeholder-1.jpg",
        "/placeholder-2.jpg",
        "/placeholder-3.jpg"
    ];

    // 엔딩 슬라이드 렌더링 (공통)
    const renderEndingSlideContent = () => {
        const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\./g, '.');

        // [SVG Map Calculation for Capture Mode]
        let pathData = "";
        let svgPoints: { x: number, y: number, name: string }[] = [];

        if (isDownloading) {
            const validSpots = course.filter(s => s.lat && s.lng);
            if (validSpots.length >= 2) {
                const lats = validSpots.map(s => parseFloat(s.lat));
                const lngs = validSpots.map(s => parseFloat(s.lng));
                let minLat = Math.min(...lats); let maxLat = Math.max(...lats);
                let minLng = Math.min(...lngs); let maxLng = Math.max(...lngs);

                // 좌표 범위가 너무 좁으면(한 장소 근처) 확대
                if (maxLat - minLat < 0.001) { minLat -= 0.005; maxLat += 0.005; }
                if (maxLng - minLng < 0.001) { minLng -= 0.005; maxLng += 0.005; }

                const padding = 0.25;
                svgPoints = validSpots.map(s => {
                    let x = (parseFloat(s.lng) - minLng) / ((maxLng - minLng) || 1);
                    let y = (parseFloat(s.lat) - minLat) / ((maxLat - minLat) || 1);
                    y = 1 - y; // Y축 반전
                    x = x * (1 - padding * 2) + padding;
                    y = y * (1 - padding * 2) + padding;
                    return { x: x * 100, y: y * 100, name: s.place_name };
                });
            } else {
                svgPoints = course.map((s, i) => ({ x: 20 + i * 30, y: 80 - i * 25, name: s.place_name })).slice(0, 3);
            }
            pathData = svgPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x}% ${p.y}%`).join(' ');
        }

        return (
            <div className="w-full h-full bg-[#FDFBF7] p-6 flex flex-col">
                {/* Header */}
                <div className="text-center mb-6 mt-2">
                    <h2 className="text-xl font-black text-gray-800 mb-1">이 시간 이렇게 보냈어요.</h2>
                    <div className="flex justify-center gap-1 text-[10px] font-bold text-gray-400">
                        {selectedAlbum?.description && <span>{selectedAlbum.description} · </span>}
                        <span>{selectedAlbum?.date || today}</span>
                        <span> · {selectedAlbum?.location || "광주"}</span>
                    </div>
                </div>

                {/* Photo Grid (Adaptive: up to 4) */}
                <div className={`grid gap-2 mb-6 ${course.length === 1 ? 'grid-cols-1' : course.length === 2 ? 'grid-cols-2' : 'grid-cols-2'}`}>
                    {course.slice(0, 4).map((spot, i) => {
                        const img = photos[i] || spot.img || placeholders[i % 3];
                        // 3개일 때 마지막 칸을 꽉 채우기 위한 로직 (옵션)
                        const isLastAndOdd = course.length === 3 && i === 2;

                        return (
                            <div key={i} className={`flex flex-col gap-2 ${isLastAndOdd ? 'col-span-2 w-1/2 mx-auto' : ''}`}>
                                <div className="w-full aspect-[16/9] rounded-xl overflow-hidden shadow-sm relative">
                                    <img src={img} className="w-full h-full object-cover" crossOrigin="anonymous" alt={`spot-${i}`} />
                                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-2 text-white pt-6">
                                        <div className="flex items-center gap-1 mb-0.5">
                                            <div className="w-3.5 h-3.5 rounded-full bg-white text-black flex items-center justify-center text-[9px] font-black">{i + 1}</div>
                                            <span className="text-[9px] font-bold truncate">{spot.place_name}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>

                {/* Route Section */}
                <div className="flex-1 flex flex-col min-h-0">
                    <div className="flex items-center gap-4 mb-3">
                        <div className="h-[1px] bg-gray-200 flex-1"></div>
                        <span className="text-[10px] font-bold text-gray-400">이 시간의 이동 루트</span>
                        <div className="h-[1px] bg-gray-200 flex-1"></div>
                    </div>

                    <div className="flex-1 bg-white rounded-xl border border-gray-100 relative overflow-hidden shadow-sm p-4">
                        {isDownloading ? (
                            <div key="capture-mode-map" className="w-full h-full relative bg-[#FDFBF7] z-50 overflow-hidden">
                                {/* 1. Tmap Static Image (Real Map) */}
                                {/* 1. Tmap Static Image (Real Map) */}
                                {(() => {
                                    const validSpots = course.filter(s => s.lat && s.lng);
                                    if (validSpots.length < 1) return <div className="absolute inset-0 bg-gray-100" />;

                                    const lats = validSpots.map(s => parseFloat(s.lat));
                                    const lngs = validSpots.map(s => parseFloat(s.lng));
                                    const minLat = Math.min(...lats); const maxLat = Math.max(...lats);
                                    const minLng = Math.min(...lngs); const maxLng = Math.max(...lngs);
                                    const centerLat = (minLat + maxLat) / 2;
                                    const centerLng = (minLng + maxLng) / 2;
                                    const maxSpan = Math.max(maxLat - minLat, maxLng - minLng);

                                    let zoom = 14;
                                    if (maxSpan > 0.1) zoom = 10;
                                    else if (maxSpan > 0.05) zoom = 11;
                                    else if (maxSpan > 0.02) zoom = 12;
                                    else if (maxSpan > 0.01) zoom = 13;

                                    const url = `https://apis.openapi.sk.com/tmap/staticMap?version=1&appKey=${process.env.NEXT_PUBLIC_TMAP_APP_KEY}&format=PNG&width=700&height=350&zoom=${zoom}&longitude=${centerLng}&latitude=${centerLat}`;

                                    return (
                                        <img
                                            src={url}
                                            className="absolute inset-0 w-full h-full object-cover opacity-90"
                                            crossOrigin="anonymous"
                                            alt="Tmap Background"
                                        />
                                    );
                                })()}

                                {/* 2. 그라데이션 오버레이 (가독성 확보) */}
                                <div className="absolute inset-0 bg-white/20 pointer-events-none"></div>

                                {/* 3. 데이터 경로 (점선 + 그림자) */}
                                <svg className="absolute inset-0 w-full h-full pointer-events-none z-10" style={{ filter: 'drop-shadow(0px 2px 2px rgba(0,0,0,0.1))' }}>
                                    <path d={pathData} fill="none" stroke="white" strokeWidth="6" strokeLinecap="round" />
                                    <path d={pathData} fill="none" stroke="#FF6B00" strokeWidth="3" strokeDasharray="6 4" strokeLinecap="round" />
                                </svg>

                                {/* 4. 마커 및 장소명 */}
                                {svgPoints.map((p, i) => (
                                    <div key={i} className="absolute flex flex-col items-center z-20" style={{ left: `${p.x}%`, top: `${p.y}%`, transform: 'translate(-50%, -50%)' }}>
                                        <div className="relative">
                                            <div className="w-8 h-8 rounded-full bg-[#FF6B00] text-white text-xs font-black flex items-center justify-center shadow-lg border-2 border-white z-10 relative">
                                                {i + 1}
                                            </div>
                                            {/* 마커 그림자 */}
                                            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-6 h-1 bg-black/20 rounded-full blur-[1px]"></div>
                                        </div>
                                        <div className="mt-1.5 px-2 py-1 bg-white/95 rounded-md shadow-sm border border-orange-100 flex flex-col items-center">
                                            <span className="text-[9px] font-bold text-gray-800 whitespace-nowrap">{p.name}</span>
                                        </div>
                                    </div>
                                ))}

                                {/* 5. 로고 워터마크 (우측 하단) */}
                                <div className="absolute bottom-3 right-3 flex items-center gap-1 opacity-60">
                                    <div className="w-2 h-2 rounded-full bg-orange-400"></div>
                                    <span className="text-[9px] text-gray-400 font-bold tracking-wider">Gwangju-On Map</span>
                                </div>
                            </div>
                        ) : (
                            <div key="interactive-mode-map" id="mini_map_div" ref={miniMapRef} className="w-full h-full rounded-lg overflow-hidden bg-gray-100 relative">
                                {!isMiniMapReady && (
                                    <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-xs bg-gray-50">
                                        지도를 불러오는 중...
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Tmap Script Load */}
                    <Script
                        src={`https://apis.openapi.sk.com/tmap/jsv2?version=1&appKey=${process.env.NEXT_PUBLIC_TMAP_APP_KEY}`}
                        onLoad={() => console.log("✅ [Timeline] Tmap Loaded")}
                        strategy="afterInteractive"
                    />

                    <div className="text-center mt-3">
                        <span className="text-[9px] text-gray-300 font-serif italic">{today} · Gwangju-On</span>
                    </div>
                </div>
            </div>
        );
    };

    // --- 1. 앨범 목록 화면 (List View) ---
    if (viewMode === 'list') {
        return (
            <div className="min-h-screen bg-[#FDFBF7] font-['Inter'] px-6 pt-12 pb-32">
                <header className="mb-12 animate-fade-in-up">
                    <h1 className="text-3xl font-black text-gray-900 mb-2">나의 여행 기록</h1>
                    <p className="text-sm text-gray-500">차곡차곡 쌓인 추억들을 꺼내보세요.</p>
                </header>

                <div className="flex flex-col gap-12 items-center">
                    {/* 새 앨범 만들기 버튼 */}
                    <button
                        onClick={() => router.push('/chat')}
                        className="w-full py-6 rounded-3xl border-2 border-dashed border-gray-300 flex items-center justify-center gap-3 text-gray-400 hover:border-[#FF6B00] hover:text-[#FF6B00] hover:bg-orange-50 transition-all group active:scale-95"
                    >
                        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center group-hover:bg-orange-100 transition-colors">
                            <Plus size={20} />
                        </div>
                        <span className="font-bold text-sm">새로운 여행 시작하기</span>
                    </button>

                    {albums.map((album, index) => {
                        // 앨범 표지용 이미지 소스 결정
                        const mainImg = album.spots && album.spots.length > 0 && album.spots[0].img ? album.spots[0].img : album.coverImg || placeholders[0];
                        const subImg1 = album.spots && album.spots.length > 1 && album.spots[1].img ? album.spots[1].img : placeholders[1];
                        const subImg2 = album.spots && album.spots.length > 2 && album.spots[2].img ? album.spots[2].img : placeholders[2];

                        return (
                            <motion.div
                                key={album.id}
                                initial={{ opacity: 0, y: 30 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.15 }}
                                onClick={() => handleAlbumClick(album)}
                                className="group cursor-pointer relative pb-4 pr-4" // Padding for the stacked photos to be visible
                            >
                                {/* --- Behind Stacked Photos (One Direction: Right/Bottom) --- */}

                                {/* Photo 3 (Back-most) */}
                                <div className="absolute top-4 left-6 w-[90%] aspect-[3/4.5] bg-white p-2 shadow-md rounded-[2px] transform rotate-[6deg] z-0 transition-transform duration-500 group-hover:rotate-[12deg] group-hover:translate-x-8 group-hover:translate-y-2 border border-gray-200">
                                    <div className="w-full h-full bg-gray-100 overflow-hidden relative grayscale-[0.2]">
                                        <img src={subImg2} className="w-full h-full object-cover opacity-80" alt="back" />
                                    </div>
                                </div>

                                {/* Photo 2 (Middle) */}
                                <div className="absolute top-2 left-3 w-[95%] aspect-[3/4.5] bg-white p-2 shadow-md rounded-[2px] transform rotate-[3deg] z-10 transition-transform duration-500 group-hover:rotate-[6deg] group-hover:translate-x-4 group-hover:translate-y-1 border border-gray-200">
                                    <div className="w-full h-full bg-gray-100 overflow-hidden relative grayscale-[0.1]">
                                        <img src={subImg1} className="w-full h-full object-cover opacity-90" alt="middle" />
                                    </div>
                                </div>

                                {/* --- Main Cover Card (Front) --- */}
                                <div className="relative z-20 bg-white p-6 shadow-xl shadow-gray-200/50 transition-all duration-500 max-w-[340px] w-full aspect-[3/4.5] flex flex-col items-center overflow-hidden border border-gray-50 transform group-hover:-translate-y-1"
                                    style={{ borderRadius: '2px' }}
                                >
                                    {/* Texture */}
                                    <div className="absolute inset-0 opacity-40 pointer-events-none z-0 mix-blend-multiply"
                                        style={{ backgroundImage: 'radial-gradient(circle at 50% 10%, #fffbf0 0%, #fff 100%)', backgroundSize: 'cover' }}
                                    />

                                    {/* 1. Title Area */}
                                    <div className="relative z-10 text-center mt-4 mb-6 w-full">
                                        <h2 className="text-2xl font-black text-gray-800 mb-2 leading-tight break-keep" style={{ wordBreak: 'keep-all' }}>{album.title}</h2>
                                        <div className="flex flex-wrap justify-center gap-1.5 text-[10px] font-bold text-gray-400">
                                            {album.description.split(' ').map((tag, i) => <span key={i}>{tag}</span>)}
                                            <span className="w-0.5 h-2 bg-gray-300 self-center mx-0.5"></span>
                                            <span>{album.date}</span>
                                        </div>
                                    </div>

                                    {/* 2. Photo Layout (Collage) */}
                                    <div className="relative w-full flex-1 mb-8 z-10">
                                        {/* Main Photo (Left, Large) */}
                                        <div className="absolute top-0 left-0 w-[65%] h-[85%] bg-white p-2 pb-6 shadow-md transform rotate-[-3deg] z-10 border border-gray-100/50 rounded-[2px]">
                                            <div className="w-full h-full bg-gray-100 overflow-hidden relative grayscale-[0.1] contrast-[1.05]">
                                                <img src={mainImg} className="w-full h-full object-cover" alt="main" />
                                            </div>
                                        </div>

                                        {/* Sub Photo 1 (Top Right) */}
                                        <div className="absolute top-4 right-0 w-[45%] h-[45%] bg-white p-1.5 pb-4 shadow-md transform rotate-[4deg] z-20 border border-gray-100/50 rounded-[2px]">
                                            <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                                <img src={subImg1} className="w-full h-full object-cover" alt="sub1" />
                                            </div>
                                        </div>

                                        {/* Sub Photo 2 (Bottom Right) */}
                                        <div className="absolute bottom-4 right-2 w-[42%] h-[42%] bg-white p-1.5 pb-4 shadow-md transform rotate-[6deg] z-30 border border-gray-100/50 rounded-[2px]">
                                            <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                                <img src={subImg2} className="w-full h-full object-cover" alt="sub2" />
                                            </div>
                                        </div>
                                    </div>

                                    {/* 3. Footer */}
                                    <div className="relative z-10 w-[90%] bg-[#FDFBF7] py-2 px-4 shadow-sm transform rotate-[1deg] mb-2 border border-gray-100/50 flex items-center justify-center gap-2">
                                        <div className="absolute inset-x-0 -top-[1px] h-[1px] border-t border-dashed border-gray-300"></div>
                                        <div className="absolute inset-x-0 -bottom-[1px] h-[1px] border-b border-dashed border-gray-300"></div>
                                        <MapPin size={12} className="text-[#FF6B00] shrink-0" />
                                        <span className="text-[10px] font-bold text-gray-500 whitespace-nowrap overflow-hidden text-ellipsis">{album.date} • {album.location}</span>
                                    </div>

                                    {/* Overlay */}
                                    <div className="absolute inset-0 bg-[#FF6B00] mix-blend-overlay opacity-[0.03] pointer-events-none z-40"></div>
                                    {album.isNew && <div className="absolute top-4 left-4 bg-[#FF6B00] text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow z-50">NEW</div>}
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {/* 하단 여백 데코 */}
                <div className="mt-20 text-center">
                    <span className="text-gray-300 text-sm font-serif italic">Keep your memories forever</span>
                </div>
            </div>
        );
    }

    // --- 2. 상세 타임라인 화면 (Detail View) ---
    if (viewMode === 'detail' && course.length === 0) {
        return (
            <div className="min-h-screen bg-[#FDFBF7] flex flex-col items-center justify-center p-6 text-center">
                <div className="fixed top-4 left-4 z-50">
                    <button onClick={() => setViewMode('list')} className="bg-white/80 backdrop-blur-md p-3 rounded-full shadow-sm border border-gray-100 hover:bg-white text-gray-700 transition-all"><ArrowLeft size={20} /></button>
                </div>
                <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mb-6 shadow-sm border border-orange-100">
                    <Calendar size={32} className="text-orange-300" />
                </div>
                <h2 className="text-xl font-black text-gray-800 mb-3">저장된 코스 정보가 없어요</h2>
            </div>
        );
    }




    return (
        <div className="min-h-screen bg-[#FDFBF7] font-['Inter'] relative pb-32">
            {/* 배경 텍스처 효과 */}
            <div className="fixed inset-0 opacity-[0.03] pointer-events-none z-0"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")` }}
            />

            {/* Back Button */}
            <div className="fixed top-4 left-4 z-50">
                <button
                    onClick={() => setViewMode('list')}
                    className="bg-white/80 backdrop-blur-md p-3 rounded-full shadow-sm border border-gray-100 hover:bg-white text-gray-700 transition-all"
                >
                    <ArrowLeft size={20} />
                </button>
            </div>

            {/* 1. 앨범 커버 (Album Cover) */}
            <section className="relative px-6 pt-12 pb-16 z-10 flex flex-col items-center">
                {/* 날짜 및 제목 */}
                <div className="text-center mb-10 animate-fade-in-up">
                    <h1 className="text-3xl font-black text-gray-900 mb-3 tracking-tight">{selectedAlbum?.title || "광주 여행"}</h1>
                    <div className="flex items-center justify-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
                        <span>{selectedAlbum?.description}</span>
                        <span>•</span>
                        <span>{selectedAlbum?.date || today}</span>
                        <span>•</span>
                        <span>{selectedAlbum?.location || "광주"}</span>
                    </div>
                </div>

                {/* 폴라로이드 콜라주 (미리보기) */}
                <div onClick={() => setIsCardModalOpen(true)} className="relative w-full max-w-[320px] aspect-[4/5] mx-auto mb-6 cursor-pointer group">
                    {/* Hover Hint */}
                    <div className="absolute inset-0 z-30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/5 rounded-xl pointer-events-none">
                        <span className="bg-white/90 px-4 py-2 rounded-full text-xs font-bold text-[#FF6B00] shadow-md flex items-center gap-1">
                            <Wand2 size={14} /> 추억 앨범 만들기
                        </span>
                    </div>

                    {/* 사진 3 */}
                    {course.length > 2 && (
                        <div className="absolute top-[45%] right-0 w-[55%] aspect-[3/4] bg-white p-2 pb-8 shadow-lg transform rotate-[6deg] rounded-sm border border-gray-100/50">
                            <div className="w-full h-full bg-gray-100 overflow-hidden">
                                <img src={photos[2] || course[2]?.img || placeholders[0]} className="w-full h-full object-cover filter sepia-[0.1]" alt="photo3" />
                            </div>
                        </div>
                    )}
                    {/* 사진 2 */}
                    {course.length > 1 && (
                        <div className="absolute top-[40%] left-0 w-[55%] aspect-[3/4] bg-white p-2 pb-8 shadow-lg transform rotate-[-5deg] rounded-sm border border-gray-100/50">
                            <div className="w-full h-full bg-gray-100 overflow-hidden">
                                <img src={photos[1] || course[1]?.img || placeholders[0]} className="w-full h-full object-cover filter sepia-[0.1]" alt="photo2" />
                            </div>
                        </div>
                    )}
                    {/* 사진 1 */}
                    <div className="absolute top-0 left-[15%] w-[70%] aspect-[3/4] bg-white p-3 pb-10 shadow-2xl transform rotate-[2deg] rounded-sm z-10 border border-gray-100/50">
                        <div className="w-full h-full bg-gray-100 overflow-hidden">
                            <img src={photos[0] || course[0]?.img || placeholders[0]} className="w-full h-full object-cover filter contrast-[1.05]" alt="photo1" />
                        </div>
                    </div>
                </div>

                <div className="relative w-full max-w-[280px] bg-white/60 backdrop-blur-sm py-3 px-6 text-center transform rotate-[-1deg] shadow-sm animate-fade-in-up delay-200">
                    <div className="absolute top-0 left-0 right-0 h-[2px] bg-transparent border-t-2 border-dashed border-gray-300"></div>
                    <div className="flex items-center justify-center gap-2 text-gray-600 font-bold text-sm">
                        <MapPin size={16} className="text-[#FF6B00]" />
                        <span>{today} • 광주 동구</span>
                    </div>
                    <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-transparent border-b-2 border-dashed border-gray-300"></div>
                </div>
            </section>

            {/* 2. 내지 (상세 코스 & 업로드) */}
            <section className="px-6 pb-20 z-10 relative">
                <div className="flex items-center gap-4 mb-8">
                    <div className="h-[1px] bg-gray-200 flex-1"></div>
                    <span className="text-xs font-bold text-gray-400">MEMORY LOG</span>
                    <div className="h-[1px] bg-gray-200 flex-1"></div>
                </div>

                <div className="space-y-12 relative">
                    <div className="absolute left-[19px] top-4 bottom-4 w-[2px] bg-gray-200 -z-10 bg-repeat-y" style={{ backgroundImage: 'linear-gradient(to bottom, #E5E7EB 50%, transparent 50%)', backgroundSize: '2px 10px' }}></div>
                    {course.map((spot, index) => (
                        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} key={index} className="flex gap-5">
                            <div className="shrink-0 relative">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center z-10 shadow-sm border-4 border-[#FDFBF7] ${photos[index] ? 'bg-[#FF6B00] text-white' : 'bg-white text-gray-400'}`}>
                                    {photos[index] ? <CheckCircle2 size={18} /> : <span className="text-sm font-black">{index + 1}</span>}
                                </div>
                            </div>
                            <div className="flex-1 bg-white p-5 rounded-2xl shadow-sm border border-gray-100/50">
                                <div className="mb-4">
                                    <h3 className="text-lg font-black text-gray-800">{spot.name}</h3>
                                    <p className="text-xs text-gray-400 mt-1">{spot.desc || "잠시 쉬기 좋은 공간"}</p>
                                </div>
                                <label className="block w-full aspect-[4/3] bg-gray-50 rounded-xl overflow-hidden relative cursor-pointer group transition-all hover:shadow-md border border-gray-100">
                                    <input type="file" accept="image/*" className="hidden" onChange={(e) => handleImageUpload(index, e)} />
                                    {photos[index] ? (
                                        <img src={photos[index]} alt="uploaded" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                                    ) : (
                                        <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-300 group-hover:text-[#FF6B00] transition-colors">
                                            <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center shadow-sm mb-2 group-hover:scale-110 transition-transform">
                                                <Camera size={24} />
                                            </div>
                                            <span className="text-xs font-bold">사진 남기기</span>
                                        </div>
                                    )}
                                    {photos[index] && (
                                        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                            <span className="bg-white/90 px-3 py-1.5 rounded-full text-xs font-bold text-gray-700 shadow-sm flex items-center gap-1">
                                                <Camera size={12} /> 수정
                                            </span>
                                            <button
                                                onClick={(e) => handleImageDelete(index, e)}
                                                className="bg-white/90 p-1.5 rounded-full text-red-500 shadow-sm hover:bg-red-50 transition-colors"
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                    )}
                                </label>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Floating Action Button */}
            <div className="fixed bottom-24 right-6 z-40">
                <button
                    onClick={() => setIsCardModalOpen(true)}
                    className="bg-[#FF6B00] text-white p-4 rounded-full shadow-xl shadow-orange-300/50 hover:scale-110 active:scale-95 transition-all flex items-center gap-2 font-bold"
                >
                    <Wand2 size={24} />
                    <span className="hidden sm:inline">추억 앨범 만들기</span>
                </button>
            </div>



            {/* Photo Album Generator Modal (Carousel) */}
            <AnimatePresence>
                {isCardModalOpen && (
                    <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center px-4">
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setIsCardModalOpen(false)} className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

                        {/* Carousel Area - Centered Vertically */}
                        <div className="flex-1 flex items-center justify-center w-full z-10 overflow-hidden relative">
                            {/* Close Button - Top Right */}
                            <div className="absolute top-4 right-4 z-50">
                                <button onClick={() => setIsCardModalOpen(false)} className="p-3 bg-white/20 rounded-full hover:bg-white/30 backdrop-blur-md text-white transition-all">
                                    <X size={24} />
                                </button>
                            </div>

                            <motion.div
                                initial={{ scale: 0.9, opacity: 0, y: 20 }}
                                animate={{ scale: 1, opacity: 1, y: 0 }}
                                exit={{ scale: 0.9, opacity: 0, y: 20 }}
                                className="relative flex flex-col items-center justify-center"
                            >
                                {/* Carousel Controls */}
                                <div className="flex items-center justify-center gap-4 sm:gap-8">
                                    {/* Prev Button */}
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setCurrentSlide(prev => Math.max(0, prev - 1)); }}
                                        disabled={currentSlide === 0}
                                        className={`p-3 rounded-full bg-white/10 backdrop-blur-md text-white hover:bg-white/20 transition-all ${currentSlide === 0 ? 'opacity-30 cursor-not-allowed' : 'opacity-100 hover:scale-110 active:scale-95'}`}
                                    >
                                        <ChevronLeft size={36} />
                                    </button>

                                    {/* The Card Content */}
                                    <div
                                        ref={cardRef}
                                        className="relative bg-white shadow-2xl overflow-hidden w-[350px] aspect-[3/4.8] rounded-[4px] flex flex-col transition-all"
                                        style={{ // Ensure it fits on small screens
                                            maxWidth: '85vw',
                                            maxHeight: '70vh',
                                            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
                                        }}
                                    >
                                        <AnimatePresence mode="wait">
                                            {/* 1. Cover Slide */}
                                            {currentSlide === 0 && (
                                                <motion.div
                                                    key="cover"
                                                    initial={{ opacity: 0, x: 20 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    exit={{ opacity: 0, x: -20 }}
                                                    transition={{ duration: 0.3 }}
                                                    className="w-full h-full flex flex-col relative"
                                                >
                                                    {/* Background */}
                                                    <div className="absolute inset-0 opacity-40 pointer-events-none z-0 mix-blend-multiply" style={{ backgroundImage: 'radial-gradient(circle at 50% 10%, #fffbf0 0%, #fff 100%)', backgroundSize: 'cover' }} />
                                                    <div className="absolute top-0 right-0 w-32 h-32 bg-orange-100/30 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
                                                    <div className="absolute bottom-0 left-0 w-40 h-40 bg-blue-100/20 rounded-full blur-3xl translate-y-1/3 -translate-x-1/3"></div>

                                                    {/* Content */}
                                                    <div className="relative z-10 flex flex-col w-full h-full p-6">
                                                        <div className="text-center mt-4 mb-8 w-full">
                                                            <h1 className="text-2xl font-black text-gray-800 mb-2 leading-tight break-keep">{selectedAlbum?.title || "광주 여행"}</h1>
                                                            <div className="flex flex-wrap justify-center gap-1.5 text-[10px] font-bold text-gray-400">
                                                                <span>{selectedAlbum?.date || today}</span>
                                                            </div>
                                                        </div>

                                                        <div className="relative w-full flex-1 mb-8">
                                                            {(() => {
                                                                // 데이터 준비
                                                                const count = course.length;
                                                                const mainImg = photos[0] || (course.length > 0 && course[0].img) || placeholders[0];
                                                                const subImg1 = photos[1] || (course.length > 1 && course[1].img) || placeholders[1];
                                                                const subImg2 = photos[2] || (course.length > 2 && course[2].img) || placeholders[2];

                                                                // [Case 1] 장소가 1개일 때: 꽉 채운 폴라로이드 1장
                                                                if (count === 1) {
                                                                    return (
                                                                        <div className="absolute top-[10%] left-[10%] right-[10%] bottom-[10%] bg-white p-3 pb-10 shadow-xl transform rotate-[-2deg] z-10 border border-gray-100/50 rounded-[2px]">
                                                                            <div className="w-full h-full bg-gray-100 overflow-hidden relative contrast-[1.05]">
                                                                                <img src={mainImg} className="w-full h-full object-cover" alt="main" crossOrigin="anonymous" />
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                }

                                                                // [Case 2] 장소가 2개일 때: 겹친 2장 (큰거 + 중간거)
                                                                if (count === 2) {
                                                                    return (
                                                                        <>
                                                                            {/* 뒤에 깔린 사진 */}
                                                                            <div className="absolute top-[20%] right-[5%] w-[60%] h-[70%] bg-white p-2 pb-6 shadow-md transform rotate-[5deg] z-0 border border-gray-100/50 rounded-[2px]">
                                                                                <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                                                                    <img src={subImg1} className="w-full h-full object-cover" alt="sub1" crossOrigin="anonymous" />
                                                                                </div>
                                                                            </div>
                                                                            {/* 메인 사진 */}
                                                                            <div className="absolute top-[5%] left-[5%] w-[65%] h-[80%] bg-white p-2 pb-6 shadow-xl transform rotate-[-3deg] z-10 border border-gray-100/50 rounded-[2px]">
                                                                                <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                                                                    <img src={mainImg} className="w-full h-full object-cover" alt="main" crossOrigin="anonymous" />
                                                                                </div>
                                                                            </div>
                                                                        </>
                                                                    );
                                                                }

                                                                // [Case 3+] 장소가 3개 이상일 때: 기존 콜라주 (메인1 + 서브2)
                                                                return (
                                                                    <>
                                                                        <div className="absolute top-0 left-0 w-[65%] h-[85%] bg-white p-2 pb-6 shadow-md transform rotate-[-3deg] z-10 border border-gray-100/50 rounded-[2px]">
                                                                            <div className="w-full h-full bg-gray-100 overflow-hidden relative grayscale-[0.1] contrast-[1.05]">
                                                                                <img src={mainImg} className="w-full h-full object-cover" alt="main" crossOrigin="anonymous" />
                                                                            </div>
                                                                        </div>
                                                                        <div className="absolute top-4 right-0 w-[45%] h-[45%] bg-white p-1.5 pb-4 shadow-md transform rotate-[4deg] z-20 border border-gray-100/50 rounded-[2px]">
                                                                            <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                                                                <img src={subImg1} className="w-full h-full object-cover" alt="sub1" crossOrigin="anonymous" />
                                                                            </div>
                                                                        </div>
                                                                        <div className="absolute bottom-4 right-2 w-[42%] h-[42%] bg-white p-1.5 pb-4 shadow-md transform rotate-[6deg] z-30 border border-gray-100/50 rounded-[2px]">
                                                                            <div className="w-full h-full bg-gray-100 overflow-hidden relative">
                                                                                <img src={subImg2} className="w-full h-full object-cover" alt="sub2" crossOrigin="anonymous" />
                                                                            </div>
                                                                        </div>
                                                                    </>
                                                                );
                                                            })()}
                                                        </div>

                                                        <div className="w-[90%] mx-auto bg-[#FDFBF7] py-2 px-4 shadow-sm transform rotate-[-1deg] border border-gray-100/50 flex items-center justify-center gap-2 relative">
                                                            <div className="absolute inset-x-0 -top-[1px] h-[1px] border-t border-dashed border-gray-300"></div>
                                                            <div className="absolute inset-x-0 -bottom-[1px] h-[1px] border-b border-dashed border-gray-300"></div>
                                                            <MapPin size={12} className="text-[#FF6B00] shrink-0" />
                                                            <span className="text-[10px] font-bold text-gray-500 whitespace-nowrap overflow-hidden text-ellipsis">{selectedAlbum?.location || "광주"}</span>
                                                        </div>
                                                    </div>
                                                    <div className="absolute inset-0 bg-[#FF6B00] mix-blend-overlay opacity-[0.03] pointer-events-none z-40"></div>
                                                </motion.div>
                                            )}

                                            {/* 2. Spot Slides */}
                                            {currentSlide > 0 && currentSlide <= course.length && (() => {
                                                const spot = course[currentSlide - 1];
                                                const displayImg = photos[currentSlide - 1] || spot.img || placeholders[(currentSlide - 1) % 3];
                                                return (
                                                    <motion.div
                                                        key={`spot-${currentSlide}`}
                                                        initial={{ opacity: 0, x: 20 }}
                                                        animate={{ opacity: 1, x: 0 }}
                                                        exit={{ opacity: 0, x: -20 }}
                                                        transition={{ duration: 0.3 }}
                                                        className="w-full h-full bg-[#FAF9F6] p-8 flex flex-col relative"
                                                    >
                                                        <div className="flex justify-between items-end border-b-2 border-dashed border-gray-200 pb-4 mb-6">
                                                            <div>
                                                                <span className="text-xs font-bold text-[#FF6B00] block mb-1">Step {currentSlide}</span>
                                                                <h2 className="text-2xl font-black text-gray-800 leading-tight">{spot.place_name}</h2>
                                                            </div>
                                                            <div className="text-right">
                                                                <span className="text-[10px] text-gray-400 block">{spot.category_group_name}</span>
                                                            </div>
                                                        </div>
                                                        <div className="w-full aspect-square bg-white p-3 shadow-lg transform rotate-1 rounded-[2px] mb-8 border border-gray-100">
                                                            <div className="w-full h-full bg-gray-100 relative overflow-hidden">
                                                                <img src={displayImg} className="w-full h-full object-cover" alt="spot" crossOrigin="anonymous" />
                                                            </div>
                                                        </div>
                                                        <div className="flex-1 bg-white p-6 rounded-lg shadow-sm border border-orange-50 relative overflow-hidden">
                                                            <div className="absolute top-0 left-0 w-1 h-full bg-[#FF6B00]"></div>
                                                            <p className="text-sm text-gray-600 leading-relaxed font-medium">
                                                                {spot.description || "이곳에서의 특별한 순간을 기록했습니다. 광주의 아름다움을 느껴보세요."}
                                                            </p>
                                                        </div>
                                                        <div className="mt-6 text-center">
                                                            <span className="text-[10px] font-bold text-gray-300">- {currentSlide} / {course.length} -</span>
                                                        </div>
                                                    </motion.div>
                                                );
                                            })()}

                                            {/* 3. Ending Slide */}
                                            {currentSlide > course.length && (
                                                <motion.div
                                                    key="ending"
                                                    initial={{ opacity: 0, x: 20 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    exit={{ opacity: 0, x: -20 }}
                                                    transition={{ duration: 0.3 }}
                                                    className="w-full h-full"
                                                >
                                                    {renderEndingSlideContent()}
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>

                                    {/* Next Button */}
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setCurrentSlide(prev => Math.min(course.length + 1, prev + 1)); }}
                                        disabled={currentSlide >= course.length + 1}
                                        className={`p-3 rounded-full bg-white/10 backdrop-blur-md text-white hover:bg-white/20 transition-all ${currentSlide >= course.length + 1 ? 'opacity-30 cursor-not-allowed' : 'opacity-100 hover:scale-110 active:scale-95'}`}
                                    >
                                        <ChevronRight size={36} />
                                    </button>
                                </div>
                                <div className="flex gap-3 mt-4 mb-6">
                                    {Array.from({ length: course.length + 2 }).map((_, i) => (
                                        <div key={i} className={`h-1.5 rounded-full transition-all duration-300 ${i === currentSlide ? 'bg-white w-8' : 'bg-white/30 w-1.5'}`}></div>
                                    ))}
                                </div>

                                {/* Download Buttons - Moved Here */}
                                <div className="flex gap-4 animate-fade-in-up mt-2">
                                    <button
                                        onClick={handleDownloadCard}
                                        disabled={isGenerating}
                                        className="px-6 py-3 bg-white text-gray-900 font-bold rounded-xl shadow-lg active:scale-95 transition-all flex items-center gap-2 hover:bg-gray-50"
                                    >
                                        {isGenerating ? (
                                            <div className="w-4 h-4 border-2 border-gray-900 border-t-transparent rounded-full animate-spin"></div>
                                        ) : (
                                            <>
                                                <Download size={18} className="text-[#FF6B00]" />
                                                <span className="text-xs">현재 페이지 저장</span>
                                            </>
                                        )}
                                    </button>
                                    <button
                                        onClick={handleDownloadAll}
                                        disabled={isGenerating}
                                        className="px-6 py-3 bg-[#FF6B00] text-white font-bold rounded-xl shadow-lg shadow-orange-900/30 active:scale-95 transition-all flex items-center gap-2 hover:bg-[#ff7b1a]"
                                    >
                                        {isGenerating ? (
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                        ) : (
                                            <>
                                                <Images size={18} />
                                                <span className="text-xs">전체 이미지 저장</span>
                                            </>
                                        )}
                                    </button>
                                </div>
                            </motion.div>
                        </div>
                    </div>
                )}
            </AnimatePresence>

            <div className="px-6 pb-12 text-center">
                <p className="text-sm text-gray-400 font-medium">모든 장소의 사진을 채워<br />나만의 지도를 완성해보세요 🎨</p>
            </div>
        </div>
    );
}
