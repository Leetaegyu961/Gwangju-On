"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Navigation2, ArrowLeft } from 'lucide-react';
import Script from 'next/script';

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

  // Load spots from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('current_course');
      console.log("📍 [MapView] Loaded from localStorage:", stored);
      if (stored) {
        const parsed = JSON.parse(stored);
        console.log("📍 [MapView] Parsed spots:", parsed);
        setSpots(parsed);
      } else {
        console.warn("⚠️ [MapView] No course data found in localStorage");
      }
    } catch (e) {
      console.error("❌ [MapView] Failed to load course", e);
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
    console.log("🎨 [MapView] Render effect triggered", {
      isMapReady,
      spotsLength: spots.length,
      hasMapInstance: !!mapInstance.current,
      hasTmap: !!(window as any).Tmapv3
    });

    if (isMapReady && spots.length > 0 && mapInstance.current && (window as any).Tmapv3) {
      console.log("🚀 [MapView] Starting marker rendering...");
      const Tmapv3 = (window as any).Tmapv3;

      // Clear existing
      markersRef.current.forEach(m => m.setMap(null));
      markersRef.current = [];
      polylinesRef.current.forEach(p => p.setMap(null));
      polylinesRef.current = [];

      const bounds = new Tmapv3.LatLngBounds();
      const path: any[] = [];

      spots.forEach((spot, index) => {
        console.log(`📍 [MapView] Adding marker ${index + 1}:`, spot.name, spot.lat, spot.lng);
        // lat/lng가 숫자인지 확인
        const lat = parseFloat(spot.lat);
        const lng = parseFloat(spot.lng);

        if (isNaN(lat) || isNaN(lng)) {
          console.error(`❌ [MapView] Invalid coordinates for ${spot.name}:`, spot.lat, spot.lng);
          return;
        }

        const position = new Tmapv3.LatLng(lat, lng);
        path.push(position);
        bounds.extend(position);

        const marker = new Tmapv3.Marker({
          position: position,
          map: mapInstance.current,
          label: `<div style="background:#0066FF; color:white; padding:4px 10px; border-radius:20px; font-weight:900; font-size:12px; border:2px solid white; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">${index + 1}</div>`,
          title: spot.name
        });
        markersRef.current.push(marker);
      });

      // Draw straight line initially (fallback)
      const polyline = new Tmapv3.Polyline({
        path: path,
        strokeColor: "#0066FF",
        strokeWeight: 4,
        strokeOpacity: 0.5,
        map: mapInstance.current,
        strokeStyle: "dashed"
      });
      polylinesRef.current.push(polyline);

      // Fit bounds to show all markers
      if (markersRef.current.length > 0) {
        console.log("📐 [MapView] Fitting bounds");
        // 지도가 완전히 로드된 후 바운드 조정 및 시트 높이 고려
        setTimeout(() => {
          mapInstance.current.fitBounds(bounds);
          // 바텀 시트(약 400px)에 가려지지 않도록 지도 중심을 살짝 아래로 이동(컨텐츠가 위로 올라감?)
          // 아니면 줌을 한 단계 낮춤?
          // panBy(x, y): x(좌우), y(상하). 
          // 시트가 아래에 있으므로, 지도의 중심점을 아래쪽 데이터까지 포함하게 해야 함 -> 
          // 사실 fitBounds하면 중앙에 오므로, 하단이 가려짐.
          // 따라서 지도를 "위쪽"을 더 보여줘야 함? 아니면 지도를 "아래"로 밀어야(pan) 핀이 위로 올라옴?
          // panBy(0, 200) -> 지도가 아래로 200px 이동 -> 핀도 아래로 이동 (더 가려짐)
          // panBy(0, -200) -> 지도가 위로 200px 이동 -> 핀이 위로 이동 (보임!)
          mapInstance.current.panBy(0, -200);
        }, 500);
      } else {
        console.warn("⚠️ [MapView] No valid markers to fit bounds");
      }
    }
  }, [spots, isMapReady]);

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

      <header className="absolute top-6 left-6 right-6 z-50 flex items-center justify-between pointer-events-none">
        <button onClick={() => router.push('/')} className="w-12 h-12 bg-white rounded-full shadow-xl flex items-center justify-center text-gray-400 pointer-events-auto">
          <ArrowLeft size={24} />
        </button>
      </header>

      <div className={`absolute bottom-0 left-0 right-0 bg-white shadow-[0_-20px_50px_rgba(0,0,0,0.1)] rounded-t-[3rem] transition-all duration-700 z-[200] ${sheetOpen ? 'h-[440px]' : 'h-[180px]'}`}>

        <div className="w-full pt-4 pb-2 cursor-pointer flex justify-center" onClick={() => setSheetOpen(!sheetOpen)}>
          <div className="w-16 h-1.5 bg-gray-200 rounded-full" />
        </div>

        {spots.length === 0 ? (
          <div className="p-8 text-center text-gray-400 font-bold">
            코스 정보가 없습니다.<br />채팅에서 여행 코스를 생성해주세요.
          </div>
        ) : (
          <div className="px-8 flex flex-col h-full overflow-hidden">
            {!sheetOpen ? (
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
      </div>

      <div className="fixed bottom-0 left-0 right-0 h-24 bg-white z-[150]" />
    </div>
  );
};
