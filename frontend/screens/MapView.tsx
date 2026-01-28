"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Navigation2, ArrowLeft } from 'lucide-react';
import Script from 'next/script';
import { motion, useAnimation, PanInfo } from 'framer-motion';

export const MapView = () => {
  const router = useRouter();
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const polylinesRef = useRef<any[]>([]);

  const [activeStep, setActiveStep] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(true);
  const [spots, setSpots] = useState<any[]>([]);
  const [isMapReady, setIsMapReady] = useState(false);
  const [isLoadingRoute, setIsLoadingRoute] = useState(false);
  const [viewMode, setViewMode] = useState<'places' | 'course'>('places');
  const [activeCategory, setActiveCategory] = useState('전체');
  const [allPlaces, setAllPlaces] = useState<any[]>([]); // Tmap 검색 결과 저장
  const [selectedPlace, setSelectedPlace] = useState<{ name: string, content: string, img?: string } | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const controls = useAnimation();

  // Tmap POI Search Function
  const searchPlaces = async () => {
    if (!mapInstance.current || !(window as any).Tmapv3) return;

    const Tmapv3 = (window as any).Tmapv3;
    const center = mapInstance.current.getCenter();
    const API_BASE_URL = "http://localhost:8000";

    // 검색 키워드 정의
    const keywordMap: { [key: string]: string } = {
      '맛집': '음식점', // "맛집"보다 "음식점"이 더 포괄적이고 정확할 수 있음
      '카페': '카페',
      '관광': '관광명소'
    };

    let keywordsToSearch: string[] = [];
    if (activeCategory === '전체') {
      keywordsToSearch = ['음식점', '카페', '관광명소'];
    } else {
      keywordsToSearch = [keywordMap[activeCategory] || activeCategory];
    }

    try {
      // 병렬 요청으로 여러 카테고리 동시 검색 (전체일 경우)
      const requests = keywordsToSearch.map(k =>
        fetch(`${API_BASE_URL}/api/tmap/poi/around?keyword=${encodeURIComponent(k)}&lat=${center.lat()}&lng=${center.lng()}&radius=1&count=${activeCategory === '전체' ? 10 : 20}`)
          .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
          })
          .then(data => ({ keyword: k, data }))
      );

      const results = await Promise.all(requests);

      let mergedPois: any[] = [];

      results.forEach(({ keyword, data }) => {
        if (data.searchPoiInfo?.pois?.poi) {
          // 키워드를 원래 카테고리명으로 매핑 (UI 표시용)
          let catLabel = activeCategory;
          if (activeCategory === '전체') {
            if (keyword === '음식점') catLabel = '맛집';
            else if (keyword === '카페') catLabel = '카페';
            else if (keyword === '관광명소') catLabel = '관광';
          }

          const pois = data.searchPoiInfo.pois.poi.map((p: any) => ({
            name: p.name,
            lat: p.noorLat,
            lng: p.noorLon,
            category: catLabel,
            address: p.upperAddrName + " " + p.middleAddrName + " " + p.lowerAddrName
          }));
          mergedPois = [...mergedPois, ...pois];
        }
      });

      // 중복 제거 (이름과 좌표가 같은 경우)
      const uniquePois = mergedPois.filter((v, i, a) => a.findIndex(t => (t.name === v.name && t.lat === v.lat)) === i);

      console.log(`📍 [MapView] Found ${uniquePois.length} places (Category: ${activeCategory})`);

      if (uniquePois.length === 0) {
        console.warn("⚠️ [MapView] No POI found");
      }
      setAllPlaces(uniquePois);

    } catch (err) {
      console.error("❌ [MapView] POI Search Error", err);
    }
  };

  // Fetch place detail from Agent
  const fetchPlaceDetail = async (name: string, address: string = "") => {
    setIsDetailLoading(true);
    setSelectedPlace({ name, content: "" }); // Reset content, keep name

    // 주소에서 동 이름 추출 (예: "광주광역시 동구 동명동 123" -> "동명동")
    let locationContext = "광주에 있는";
    if (address) {
      const parts = address.split(" ");
      // 보통 '동'으로 끝나는 부분이 3번째 혹은 4번째에 위치함 (시/도 구/군 읍/면/동)
      // 간단히 '동'으로 끝나는 단어를 찾아서 문맥 추가
      const dong = parts.find(p => p.endsWith("동") || p.endsWith("가") || p.endsWith("로"));
      if (dong) {
        locationContext = `${dong}에 있는`;
      }
    }

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `${locationContext} ${name}에 대해 간단히 소개해줘. 특징 1가지와 방문객 리뷰 핵심 1가지만 짧은 개조식(bullet point)으로 알려줘.`,
          userId: "user_map_view"
        })
      });

      const data = await response.json();

      // 이미지 추출 (EvidenceCards가 있다면 첫 번째 이미지 사용)
      let imgUrl = undefined;
      if (data.evidenceCards && data.evidenceCards.length > 0) {
        imgUrl = data.evidenceCards[0].img;
      }

      setSelectedPlace({ name, content: data.text, img: imgUrl });
    } catch (e) {
      console.error("❌ [MapView] Detail fetch error", e);
      setSelectedPlace({ name, content: "정보를 불러오는 데 실패했어요." });
    } finally {
      setIsDetailLoading(false);
    }
  };

  // Sheet height constants

  // Sheet height constants
  const OPEN_HEIGHT = 440;
  const CLOSED_HEIGHT = 180;

  // Load spots from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('current_course');
      if (stored) {
        const parsed = JSON.parse(stored);
        setSpots(parsed);
        setViewMode('course'); // 코스가 있으면 코스 모드로 시작
      } else {
        // 코스가 없으면 장소 모드로 시작하고 초기 검색 시도 (지도가 로드된 후)
        setViewMode('places');
      }
    } catch (e) {
      console.error("❌ [MapView] Failed to load data", e);
    }
  }, []);

  // Initialize Map - 첫 번째 장소 좌표를 초기 중심으로 사용
  const initMap = () => {
    console.log("🗺️ [MapView] initMap called");
    if (typeof window === 'undefined' || !(window as any).Tmapv3) {
      console.error("❌ [MapView] Tmapv3 not loaded");
      return;
    }

    if (mapInstance.current) {
      console.log("ℹ️ [MapView] Map instance already exists");
      return;
    }

    const Tmapv3 = (window as any).Tmapv3;

    // 첫 번째 마커 위치로 초기화, 없으면 광주 시청
    let initialLat = 35.1595;
    let initialLng = 126.8526;

    const storedCourse = localStorage.getItem('current_course');
    if (storedCourse) {
      try {
        const parsed = JSON.parse(storedCourse);
        if (parsed.length > 0 && parsed[0].lat && parsed[0].lng) {
          initialLat = parseFloat(parsed[0].lat);
          initialLng = parseFloat(parsed[0].lng);
          console.log("📍 [MapView] Using first spot as initial center:", initialLat, initialLng);
        }
      } catch (e) { /* ignore */ }
    }

    mapInstance.current = new Tmapv3.Map(mapRef.current, {
      center: new Tmapv3.LatLng(initialLat, initialLng),
      width: "100%",
      height: "100%",
      zoom: 15, // 조금 더 확대해서 시작
      zoomControl: false,
    });

    console.log("✅ [MapView] Map instance created");
    setIsMapReady(true);
  };

  // Render initial markers and adjust bounds
  useEffect(() => {
    if (isMapReady && mapInstance.current && (window as any).Tmapv3) {
      const Tmapv3 = (window as any).Tmapv3;

      // Clear existing
      markersRef.current.forEach(m => m.setMap(null));
      markersRef.current = [];
      polylinesRef.current.forEach(p => p.setMap(null));
      polylinesRef.current = [];

      const bounds = new Tmapv3.LatLngBounds();
      const path: any[] = [];

      // 표시할 데이터 결정 (코스 모드 vs 주변 장소 모드)
      // 장소 모드일 때는 allPlaces(검색 결과)를 사용
      const displayData = viewMode === 'course' ? spots : allPlaces;

      displayData.forEach((spot, index) => {
        const lat = parseFloat(spot.lat);
        const lng = parseFloat(spot.lng);
        if (isNaN(lat) || isNaN(lng)) return;

        const position = new Tmapv3.LatLng(lat, lng);
        path.push(position);
        bounds.extend(position);

        let markerIcon = "📍";
        let markerBg = "white";
        let markerBorder = "#0066FF";

        if (viewMode === 'places') {
          if (spot.category === '맛집') {
            markerIcon = "🍴";
            markerBg = "#FFF0F0";
            markerBorder = "#FF4444";
          } else if (spot.category === '카페') {
            markerIcon = "☕";
            markerBg = "#F0F5FF";
            markerBorder = "#4488FF";
          } else if (spot.category === '관광') {
            markerIcon = "🎡";
            markerBg = "#F0FFF4";
            markerBorder = "#00C853";
          }
        }

        const markerContent = viewMode === 'course'
          ? `<div style="background:#0066FF; color:white; padding:4px 10px; border-radius:20px; font-weight:900; font-size:12px; border:2px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); cursor: pointer; pointer-events: auto;">${index + 1}</div>`
          : `<div style="background:${markerBg}; color:${markerBorder}; padding:6px; border-radius:50%; width:32px; height:32px; display:flex; items-center; justify-content:center; border:2px solid ${markerBorder}; box-shadow: 0 4px 12px rgba(0,0,0,0.1); font-size:16px; cursor: pointer; pointer-events: auto;">${markerIcon}</div>`;

        const marker = new Tmapv3.Marker({
          position: position,
          map: mapInstance.current,
          iconHTML: markerContent,
          title: spot.name
        });

        // Marker Click Event
        // Marker Click Event
        // Tmapv3 uses 'Click' or 'click'. We attach both to be safe, or use .on if .addListener isn't supported properly.
        // Also styling cursor to pointer to indicate clickability.
        if (marker.on) {
          marker.on("Click", () => {
            const addr = spot.address || "";
            fetchPlaceDetail(spot.name, addr);
            setSheetOpen(true); // Open sheet to show details
          });
          // Some versions might use lowercase
          marker.on("click", () => {
            const addr = spot.address || "";
            fetchPlaceDetail(spot.name, addr);
            setSheetOpen(true); // Open sheet to show details
          });
        } else if (marker.addListener) {
          marker.addListener("click", () => {
            const addr = spot.address || "";
            fetchPlaceDetail(spot.name, addr);
            setSheetOpen(true); // Open sheet to show details
          });
        }

        markersRef.current.push(marker);
      });

      if (viewMode === 'course' && displayData.length > 1) {
        const polyline = new Tmapv3.Polyline({
          path: path,
          strokeColor: "#0066FF",
          strokeWeight: 4,
          strokeOpacity: 0.5,
          map: mapInstance.current,
          strokeStyle: "dashed"
        });
        polylinesRef.current.push(polyline);
      }

      if (displayData.length > 0 && viewMode === 'course') {
        setTimeout(() => {
          mapInstance.current.fitBounds(bounds);
          mapInstance.current.panBy(0, -100);
        }, 500);
      }
    }
  }, [spots, allPlaces, viewMode, activeCategory, isMapReady]);

  // Route mode state: 'pedestrian' or 'car'
  const [routeMode, setRouteMode] = useState<'pedestrian' | 'car'>('pedestrian');
  const [totalTime, setTotalTime] = useState<number>(0); // 초 단위

  // Fetch and draw route based on mode
  const fetchRoute = async (mode: 'pedestrian' | 'car') => {
    if (!isMapReady || spots.length < 2) return;
    setIsLoadingRoute(true);
    setRouteMode(mode);

    const Tmapv3 = (window as any).Tmapv3;
    const APP_KEY = process.env.NEXT_PUBLIC_TMAP_APP_KEY || "";

    try {
      // Clear existing routes
      polylinesRef.current.forEach(p => p.setMap(null));
      polylinesRef.current = [];

      let accumulatedTime = 0;
      const routeEndpoint = mode === 'pedestrian'
        ? 'https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json'
        : 'https://apis.openapi.sk.com/tmap/routes?version=1&format=json';

      for (let i = 0; i < spots.length - 1; i++) {
        const start = spots[i];
        const end = spots[i + 1];

        const response = await fetch(routeEndpoint, {
          method: 'POST',
          headers: {
            'appKey': APP_KEY,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            startX: String(start.lng),
            startY: String(start.lat),
            endX: String(end.lng),
            endY: String(end.lat),
            reqCoordType: "WGS84GEO",
            resCoordType: "WGS84GEO",
            startName: encodeURIComponent(start.name),
            endName: encodeURIComponent(end.name)
          })
        });

        const data = await response.json();

        if (data.features) {
          const linePath: any[] = [];
          data.features.forEach((feature: any) => {
            // 시간 정보 추출
            if (feature.properties?.totalTime) {
              accumulatedTime += feature.properties.totalTime;
            }
            if (feature.geometry.type === "LineString") {
              feature.geometry.coordinates.forEach((coord: any) => {
                linePath.push(new Tmapv3.LatLng(coord[1], coord[0]));
              });
            }
          });

          // 경로 색상: 도보=파랑, 차량=초록
          const routeColor = mode === 'pedestrian' ? "#0066FF" : "#00C853";
          const routePolyline = new Tmapv3.Polyline({
            path: linePath,
            strokeColor: routeColor,
            strokeWeight: 6,
            map: mapInstance.current
          });
          polylinesRef.current.push(routePolyline);
        }
      }

      setTotalTime(accumulatedTime);
      console.log(`✅ ${mode} route loaded. Total time: ${Math.round(accumulatedTime / 60)} min`);

    } catch (error) {
      console.error("Route fetch failed", error);
      alert("경로를 불러오는데 실패했습니다.");
    } finally {
      setIsLoadingRoute(false);
    }
  };

  // Helper: format seconds to "X분"
  const formatTime = (seconds: number) => {
    const mins = Math.round(seconds / 60);
    if (mins < 60) return `${mins}분`;
    const hours = Math.floor(mins / 60);
    const remainMins = mins % 60;
    return `${hours}시간 ${remainMins}분`;
  };


  // Active step change -> move map center
  useEffect(() => {
    if (mapInstance.current && (window as any).Tmapv3 && spots[activeStep]) {
      const Tmapv3 = (window as any).Tmapv3;
      const pos = new Tmapv3.LatLng(spots[activeStep].lat, spots[activeStep].lng);
      mapInstance.current.panTo(pos);
    }
  }, [activeStep, spots]);

  const nextStep = () => setActiveStep(prev => (prev < spots.length - 1 ? prev + 1 : prev));
  const prevStep = () => setActiveStep(prev => (prev > 0 ? prev - 1 : prev));

  // Handle Drag End to snap to Open or Closed
  const handleDragEnd = (_: any, info: PanInfo) => {
    const shouldClose = info.velocity.y > 20 || info.offset.y > 100;
    const shouldOpen = info.velocity.y < -20 || info.offset.y < -100;

    if (shouldClose) {
      setSheetOpen(false);
    } else if (shouldOpen) {
      setSheetOpen(true);
    }
  };

  // Sync sheetOpen state with animation
  useEffect(() => {
    controls.start({
      height: sheetOpen ? OPEN_HEIGHT : CLOSED_HEIGHT,
      transition: { type: 'spring', damping: 25, stiffness: 200 }
    });
  }, [sheetOpen, controls]);

  // Tmap 로드 감지 및 초기화 (Safety Check)
  useEffect(() => {
    const checkTmap = setInterval(() => {
      if ((window as any).Tmapv3 && !mapInstance.current) {
        console.log("🔄 [MapView] Tmapv3 detected via interval, initializing...");
        initMap();
        clearInterval(checkTmap);
      }
    }, 1000); // 1초마다 체크
    return () => clearInterval(checkTmap);
  }, []);

  return (
    <div className="h-screen bg-gray-50 relative overflow-hidden font-['Inter']">

      <div
        ref={mapRef}
        id="map_div"
        className="absolute inset-0 z-0 bg-[#E5E7EB]"
        style={{ height: "100vh" }}
      />

      <header className="absolute top-0 left-0 right-0 z-50 bg-white shadow-sm flex flex-col pointer-events-auto">
        <div className="flex items-center px-6 py-4">
          <button onClick={() => router.push('/')} className="mr-4 text-gray-900">
            <ArrowLeft size={24} />
          </button>
          <h1 className="text-xl font-black text-gray-900 flex items-center gap-2">
            <span className="text-[#0066FF]">📍</span> 내주변
          </h1>
        </div>

        <div className="flex border-b">
          <button
            onClick={() => setViewMode('places')}
            className={`flex-1 py-3 text-sm font-black transition-all ${viewMode === 'places' ? 'text-[#0066FF] border-b-2 border-[#0066FF]' : 'text-gray-400'}`}
          >
            장소
          </button>
          <button
            onClick={() => setViewMode('course')}
            className={`flex-1 py-3 text-sm font-black transition-all ${viewMode === 'course' ? 'text-[#0066FF] border-b-2 border-[#0066FF]' : 'text-gray-400'}`}
          >
            코스
          </button>
        </div>

        <div className="px-6 py-4 flex gap-2 overflow-x-auto no-scrollbar bg-gray-50/50">
          {['전체', '맛집', '카페', '관광'].map((cat) => (
            <button
              key={cat}
              onClick={() => {
                setActiveCategory(cat);
                setViewMode('places'); // 카테고리 클릭 시 장소 모드로 전환
                // 상태 업데이트 후 검색은 useEffect 또는 즉시 호출 고민 -> 여기서는 검색 트리거를 위해 의존성 활용
                setTimeout(searchPlaces, 100);
              }}
              className={`px-5 py-2 rounded-full text-xs font-black whitespace-nowrap transition-all shadow-sm ${activeCategory === cat
                ? 'bg-[#0066FF] text-white'
                : 'bg-white text-gray-600 border border-gray-100'
                }`}
            >
              {cat === '맛집' ? '🍴 ' : cat === '카페' ? '☕ ' : cat === '관광' ? '🎡 ' : 'ALL '}
              {cat}
            </button>
          ))}
        </div>
      </header>

      <div className="absolute top-[180px] left-1/2 -translate-x-1/2 z-40">
        <button
          onClick={searchPlaces}
          className="bg-white/90 backdrop-blur-md px-6 py-2.5 rounded-full shadow-2xl border border-white/50 text-[#0066FF] font-black text-sm flex items-center gap-2 active:scale-95 transition-all">
          <span className="animate-spin-slow text-lg">🔄</span>
          현 지도에서 검색
        </button>
      </div>

      <motion.div
        drag="y"
        dragConstraints={{ top: 0, bottom: 0 }}
        dragElastic={0.1}
        onDragEnd={handleDragEnd}
        animate={controls}
        initial={{ height: OPEN_HEIGHT }}
        className="absolute bottom-0 left-0 right-0 bg-white shadow-[0_-20px_50px_rgba(0,0,0,0.1)] rounded-t-[3rem] z-[200] overflow-hidden"
      >
        <div className="w-full pt-4 pb-2 cursor-grab active:cursor-grabbing flex justify-center touch-none">
          <div className="w-16 h-1.5 bg-gray-200 rounded-full" />
        </div>

        {spots.length === 0 && !selectedPlace && !isDetailLoading ? (
          <div className="p-8 text-center text-gray-400 font-bold">
            코스 정보가 없습니다.<br />채팅에서 여행 코스를 생성해주세요.
          </div>
        ) : (
          <div className="px-8 flex flex-col h-full overflow-hidden">
            {/* 1. Detail View Mode */}
            {(selectedPlace || isDetailLoading) ? (
              <div className="animate-fade-in space-y-4 pt-2 h-full flex flex-col">
                {/* Header with Back Button */}
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => {
                      setSelectedPlace(null);
                      setIsDetailLoading(false);
                    }}
                    className="flex items-center gap-1 text-gray-500 hover:text-gray-900 transition-colors"
                  >
                    <ArrowLeft size={20} />
                    <span className="text-sm font-bold">목록으로</span>
                  </button>
                  <span className="text-xs font-bold text-[#0066FF] bg-blue-50 px-3 py-1 rounded-full">AI 장소 분석</span>
                </div>

                {/* Title */}
                <h3 className="text-2xl font-black text-gray-900 border-b border-gray-100 pb-3">
                  {selectedPlace?.name || "장소 정보 검색 중..."}
                </h3>

                {/* Loading State */}
                {isDetailLoading ? (
                  <div className="flex flex-col items-center justify-center py-10 gap-4">
                    <div className="w-10 h-10 border-4 border-[#0066FF] border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-sm text-gray-500 font-medium animate-pulse">
                      AI 에이전트가 정보를 찾고 있어요...
                    </p>
                  </div>
                ) : (
                  /* Content State */
                  <div className="flex-1 overflow-y-auto custom-scrollbar pb-20">
                    {selectedPlace?.img && (
                      <div className="relative w-full h-48 rounded-2xl overflow-hidden mb-5 shadow-sm bg-gray-100">
                        <img
                          src={selectedPlace.img}
                          alt={selectedPlace.name}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      </div>
                    )}

                    <div className="bg-gray-50 p-5 rounded-2xl text-sm text-gray-700 leading-relaxed whitespace-pre-line border border-gray-100 font-medium shadow-sm">
                      {selectedPlace?.content}
                    </div>

                    <div className="mt-4">
                      <button
                        onClick={() => {
                          setSelectedPlace(null);
                          setIsDetailLoading(false);
                        }}
                        className="w-full py-4 bg-[#0066FF] text-white font-bold rounded-xl active:scale-95 transition-all shadow-lg shadow-blue-100"
                      >
                        확인 완료
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : !sheetOpen ? (
              // 2. Collapsed Course View
              <div className="flex items-center justify-between py-4 animate-fade-in">
                <div className="flex-1">
                  <span className="text-[10px] font-black text-[#0066FF] uppercase tracking-widest mb-1 block">최적 경로 분석 완료</span>
                  <h2 className="text-xl font-black text-gray-900 tracking-tight">
                    {activeStep + 1}. {spots[activeStep].name}
                  </h2>
                  <span className="text-gray-300 font-bold text-sm">다음 장소까지 {spots[activeStep].transport}</span>
                </div>
                <button
                  onClick={() => setSheetOpen(true)}
                  className="w-14 h-14 bg-[#0066FF] text-white rounded-2xl flex items-center justify-center shadow-lg shadow-blue-100 active:scale-95 transition-all"
                >
                  <Navigation2 size={24} fill="currentColor" />
                </button>
              </div>
            ) : (
              <div className="animate-fade-in space-y-6 pt-2">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-black text-gray-900 tracking-tight">단계 {activeStep + 1} / {spots.length}</span>
                    <span className="text-[10px] font-bold text-[#0066FF] bg-blue-50 px-3 py-1 rounded-full">Tmap 실시간 데이터</span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-[#0066FF] transition-all duration-700" style={{ width: `${((activeStep + 1) / spots.length) * 100}%` }} />
                  </div>
                </div>

                <div className="flex gap-6 items-center">
                  <div className="w-24 h-24 rounded-3xl overflow-hidden shadow-md shrink-0">
                    <img src={spots[activeStep].img} className="w-full h-full object-cover" alt="place" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-xl font-black text-gray-900 mb-2 truncate">{spots[activeStep].name}</h3>
                    <p className="text-xs font-bold text-gray-400 leading-relaxed mb-3 line-clamp-2">{spots[activeStep].desc}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {spots[activeStep].tags.map((t: string) => (
                        <span key={t} className="px-2 py-1 bg-gray-50 rounded-md text-[10px] font-black text-gray-400">{t}</span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button onClick={prevStep} disabled={activeStep === 0} className="flex-1 py-4 bg-gray-50 text-gray-400 rounded-2xl font-black text-sm disabled:opacity-30">이전</button>
                  <button onClick={nextStep} disabled={activeStep === spots.length - 1} className="flex-1 py-4 bg-gray-100 text-gray-800 rounded-2xl font-black text-sm disabled:opacity-30">다음 장소</button>
                </div>

                {/* 경로 모드 선택 버튼 */}
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => fetchRoute('pedestrian')}
                    disabled={isLoadingRoute}
                    className={`flex-1 py-4 rounded-2xl font-black text-sm transition-all flex flex-col items-center gap-1 ${routeMode === 'pedestrian' ? 'bg-[#0066FF] text-white shadow-lg' : 'bg-gray-100 text-gray-600'
                      } disabled:opacity-50`}
                  >
                    <span>🚶 도보</span>
                    {totalTime > 0 && routeMode === 'pedestrian' && (
                      <span className="text-xs opacity-80">{formatTime(totalTime)}</span>
                    )}
                  </button>
                  <button
                    onClick={() => fetchRoute('car')}
                    disabled={isLoadingRoute}
                    className={`flex-1 py-4 rounded-2xl font-black text-sm transition-all flex flex-col items-center gap-1 ${routeMode === 'car' ? 'bg-[#00C853] text-white shadow-lg' : 'bg-gray-100 text-gray-600'
                      } disabled:opacity-50`}
                  >
                    <span>🚗 차량</span>
                    {totalTime > 0 && routeMode === 'car' && (
                      <span className="text-xs opacity-80">{formatTime(totalTime)}</span>
                    )}
                  </button>
                </div>
                {isLoadingRoute && (
                  <div className="text-center text-sm text-gray-400 mt-2 animate-pulse">경로를 불러오는 중...</div>
                )}
              </div>
            )}
          </div>
        )}
      </motion.div>

      <div className="fixed bottom-0 left-0 right-0 h-24 bg-white z-[150]" />
    </div>
  );
};
