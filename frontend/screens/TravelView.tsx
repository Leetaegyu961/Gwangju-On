"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Locate, Check, MapPin, Navigation2, ChevronLeft, ChevronRight, Camera, X } from 'lucide-react';
import { motion, useAnimation, PanInfo } from 'framer-motion';
import { getCourseImage } from '../utils/courseImages';

// Fix for React 19 / Framer Motion type mismatch
const MotionDiv = motion.div as any;

// --------------------------------------------------------------------------
// Helper Functions
// --------------------------------------------------------------------------
const formatTime = (seconds: number) => {
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins}분`;
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return `${hours}시간 ${remainMins}분`;
};

const ensureIds = (places: any[]) => {
  if (!places || !Array.isArray(places)) return [];
  return places.map((p, i) => ({
    ...p,
    id: p.id || `spot-${Date.now()}-${i}`
  }));
};

// --------------------------------------------------------------------------
// TravelView Component
// --------------------------------------------------------------------------
export default function TravelView() {
  const router = useRouter();

  // ---- State ----

  // Course data
  const [spots, setSpots] = useState<any[]>([]);
  const [courseMeta, setCourseMeta] = useState<any>(null);

  // Travel progress
  const [activeStep, setActiveStep] = useState(0);
  const [visitedSteps, setVisitedSteps] = useState<Set<number>>(new Set());

  // Map
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const polylinesRef = useRef<any[]>([]);
  const routePolylinesRef = useRef<any[]>([]); // TMap 실제 경로 폴리라인
  const routeCacheRef = useRef<Map<string, any[]>>(new Map()); // 경로 캐시 (구간별)
  const [isMapReady, setIsMapReady] = useState(false);
  const [isRouteLoaded, setIsRouteLoaded] = useState(false);

  // UI
  const [sheetOpen, setSheetOpen] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);
  const controls = useAnimation();

  // Bottom sheet constants
  const OPEN_HEIGHT = 420;
  const CLOSED_HEIGHT = 140;

  // ---- Toast auto-dismiss ----
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  // ---- Load course data from localStorage ----
  useEffect(() => {
    try {
      const storedCourse = localStorage.getItem('current_course');
      const storedMeta = localStorage.getItem('current_course_meta');
      const storedVisited = localStorage.getItem('travel_visited_steps');

      if (storedCourse) {
        const parsed = JSON.parse(storedCourse);
        // Restore images
        const isLocal = window.location.hostname === 'localhost';
        const restored = parsed.map((p: any) => {
          let imgUrl = p.img;
          if (imgUrl && imgUrl.includes('localhost') && !isLocal) {
            imgUrl = null;
          }
          if (!imgUrl && p.photo_name) {
            const baseUrl = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/api\/?$/, '');
            imgUrl = `${baseUrl}/api/photo?name=${p.photo_name}`;
          }
          return {
            ...p,
            img: imgUrl || getCourseImage([p.type || '장소'], p.name || '')
          };
        });
        setSpots(ensureIds(restored));
      } else {
        // No course data, go back to map
        router.push('/map');
        return;
      }

      if (storedMeta) {
        setCourseMeta(JSON.parse(storedMeta));
      }

      if (storedVisited) {
        setVisitedSteps(new Set(JSON.parse(storedVisited)));
      }
    } catch (e) {
      console.error('[TravelView] Failed to load data', e);
      router.push('/map');
    }
  }, [router]);

  // ---- TMap Init ----
  const initMap = useCallback(() => {
    if (typeof window === 'undefined' || !(window as any).Tmapv3) return;
    if (mapInstance.current) return;

    const Tmapv3 = (window as any).Tmapv3;

    let initialLat = 35.1595;
    let initialLng = 126.8526;

    if (spots.length > 0 && spots[0].lat && spots[0].lng) {
      initialLat = parseFloat(spots[0].lat);
      initialLng = parseFloat(spots[0].lng);
    }

    mapInstance.current = new Tmapv3.Map(mapRef.current, {
      center: new Tmapv3.LatLng(initialLat, initialLng),
      width: "100%",
      height: "100%",
      zoom: 15,
      zoomControl: false,
    });

    setIsMapReady(true);

    // Map click handler: close sheet
    mapInstance.current.on("Click", () => {
      if (sheetOpen) setSheetOpen(false);
    });
  }, [spots, sheetOpen]);

  // Check for TMap SDK load
  useEffect(() => {
    if (spots.length === 0) return;

    const checkTmap = setInterval(() => {
      if ((window as any).Tmapv3 && !mapInstance.current) {
        initMap();
        clearInterval(checkTmap);
      }
    }, 500);

    // Also try immediately
    if ((window as any).Tmapv3 && !mapInstance.current) {
      initMap();
      clearInterval(checkTmap);
    }

    return () => clearInterval(checkTmap);
  }, [spots, initMap]);

  // ---- Render Markers (3-color system) ----
  useEffect(() => {
    if (!isMapReady || !mapInstance.current || !(window as any).Tmapv3) return;
    if (spots.length === 0) return;

    const Tmapv3 = (window as any).Tmapv3;

    // Clear existing
    markersRef.current.forEach(m => m.setMap(null));
    markersRef.current = [];
    polylinesRef.current.forEach(p => p.setMap(null));
    polylinesRef.current = [];

    const bounds = new Tmapv3.LatLngBounds();
    const allPositions: any[] = [];

    spots.forEach((spot, index) => {
      const lat = parseFloat(spot.lat);
      const lng = parseFloat(spot.lng);
      if (isNaN(lat) || isNaN(lng)) return;

      const position = new Tmapv3.LatLng(lat, lng);
      allPositions.push(position);
      bounds.extend(position);

      const isVisited = visitedSteps.has(index);
      const isCurrent = index === activeStep;

      // Marker color logic
      let bgColor = '#CBD5E1'; // upcoming (gray)
      let borderColor = '#94A3B8';
      let textColor = '#64748B';
      let shadowColor = 'rgba(0,0,0,0.1)';
      let pulseAnimation = '';
      let markerContent = '';

      if (isVisited) {
        // Visited (green)
        bgColor = '#00C853';
        borderColor = '#00E676';
        textColor = 'white';
        shadowColor = 'rgba(0,200,83,0.3)';
        markerContent = `<div style="
          background:${bgColor}; color:${textColor};
          width:36px; height:36px; border-radius:50%;
          display:flex; align-items:center; justify-content:center;
          font-weight:900; font-size:14px;
          border:3px solid white;
          box-shadow: 0 4px 12px ${shadowColor};
          cursor:pointer; pointer-events:auto;
        "><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg></div>`;
      } else if (isCurrent) {
        // Current (blue with pulse)
        bgColor = '#0066FF';
        borderColor = '#3388FF';
        textColor = 'white';
        shadowColor = 'rgba(0,102,255,0.4)';
        markerContent = `<div style="
          background:${bgColor}; color:${textColor};
          width:40px; height:40px; border-radius:50%;
          display:flex; align-items:center; justify-content:center;
          font-weight:900; font-size:15px;
          border:3px solid white;
          box-shadow: 0 4px 16px ${shadowColor}, 0 0 0 8px rgba(0,102,255,0.15);
          cursor:pointer; pointer-events:auto;
          animation: travelPulse 2s ease-in-out infinite;
        ">${index + 1}</div>`;
      } else {
        // Upcoming (gray)
        markerContent = `<div style="
          background:${bgColor}; color:${textColor};
          width:32px; height:32px; border-radius:50%;
          display:flex; align-items:center; justify-content:center;
          font-weight:900; font-size:12px;
          border:2px solid white;
          box-shadow: 0 2px 8px ${shadowColor};
          cursor:pointer; pointer-events:auto;
          opacity:0.7;
        ">${index + 1}</div>`;
      }

      const marker = new Tmapv3.Marker({
        position: position,
        map: mapInstance.current,
        iconHTML: markerContent,
      });

      // Click to focus
      const onMarkerClick = () => {
        setActiveStep(index);
        setSheetOpen(true);
      };

      if (marker.on) {
        marker.on("Click", onMarkerClick);
        marker.on("click", onMarkerClick);
      } else if (marker.addListener) {
        marker.addListener("click", onMarkerClick);
      }

      markersRef.current.push(marker);
    });

    // Fit bounds
    if (allPositions.length > 0) {
      setTimeout(() => {
        if (mapInstance.current) {
          mapInstance.current.fitBounds(bounds, {
            top: 100,
            bottom: sheetOpen ? 300 : 160,
            left: 40,
            right: 40
          });
        }
      }, 150);
    }
  }, [spots, visitedSteps, activeStep, isMapReady]);

  // ---- Fetch & Draw TMap Route Polylines ----
  const fetchAndDrawRoutes = useCallback(async () => {
    if (!isMapReady || !mapInstance.current || !(window as any).Tmapv3) return;
    if (spots.length < 2) return;

    const Tmapv3 = (window as any).Tmapv3;
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

    // Clear existing route polylines
    routePolylinesRef.current.forEach(p => p.setMap(null));
    routePolylinesRef.current = [];

    for (let i = 0; i < spots.length - 1; i++) {
      const start = spots[i];
      const end = spots[i + 1];
      const cacheKey = `${start.lat},${start.lng}-${end.lat},${end.lng}`;
      const segmentVisited = visitedSteps.has(i) && visitedSteps.has(i + 1);

      let linePath: any[] = [];

      // Use cache if available
      if (routeCacheRef.current.has(cacheKey)) {
        const cachedCoords = routeCacheRef.current.get(cacheKey)!;
        linePath = cachedCoords.map((c: number[]) => new Tmapv3.LatLng(c[0], c[1]));
      } else {
        try {
          const response = await fetch(`${API_BASE_URL}/tmap/routes/pedestrian`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
            const coords: number[][] = [];
            data.features.forEach((feature: any) => {
              if (feature.geometry.type === "LineString") {
                feature.geometry.coordinates.forEach((coord: any) => {
                  coords.push([coord[1], coord[0]]);
                  linePath.push(new Tmapv3.LatLng(coord[1], coord[0]));
                });
              }
            });
            // Cache the raw coords
            routeCacheRef.current.set(cacheKey, coords);
          }
        } catch (error) {
          console.error(`[TravelView] Route fetch failed for segment ${i}`, error);
          // Fallback to straight line
          linePath = [
            new Tmapv3.LatLng(parseFloat(start.lat), parseFloat(start.lng)),
            new Tmapv3.LatLng(parseFloat(end.lat), parseFloat(end.lng))
          ];
        }
      }

      if (linePath.length > 0) {
        const polyline = new Tmapv3.Polyline({
          path: linePath,
          strokeColor: segmentVisited ? "#00C853" : "#0066FF",
          strokeWeight: segmentVisited ? 6 : 4,
          strokeOpacity: segmentVisited ? 0.9 : 0.5,
          map: mapInstance.current,
          strokeStyle: segmentVisited ? "solid" : "dash",
        });
        routePolylinesRef.current.push(polyline);
      }
    }

    setIsRouteLoaded(true);
  }, [isMapReady, spots, visitedSteps]);

  // Fetch routes when map is ready and spots are loaded
  useEffect(() => {
    if (isMapReady && spots.length >= 2) {
      fetchAndDrawRoutes();
    }
  }, [isMapReady, spots, visitedSteps, fetchAndDrawRoutes]);

  // ---- Pan map to active step ----
  useEffect(() => {
    if (mapInstance.current && (window as any).Tmapv3 && spots[activeStep]) {
      const Tmapv3 = (window as any).Tmapv3;
      const pos = new Tmapv3.LatLng(spots[activeStep].lat, spots[activeStep].lng);
      mapInstance.current.panTo(pos);
    }
  }, [activeStep, spots]);

  // ---- Bottom sheet drag ----
  const handleDragEnd = (_: any, info: PanInfo) => {
    if (info.velocity.y > 20 || info.offset.y > 100) {
      setSheetOpen(false);
    } else if (info.velocity.y < -20 || info.offset.y < -100) {
      setSheetOpen(true);
    }
  };

  useEffect(() => {
    controls.start({
      height: sheetOpen ? OPEN_HEIGHT : CLOSED_HEIGHT,
      transition: { type: 'spring', damping: 25, stiffness: 200 }
    });
  }, [sheetOpen, controls]);

  // ---- Arrival Handlers ----
  const handleArrival = (stepIndex: number) => {
    const newVisited = new Set(visitedSteps);
    newVisited.add(stepIndex);
    setVisitedSteps(newVisited);
    localStorage.setItem('travel_visited_steps', JSON.stringify([...newVisited]));

    // Add to memory_spots
    const memorySpots = JSON.parse(localStorage.getItem('memory_spots') || '[]');
    const alreadyAdded = memorySpots.some((s: any) => s.name === spots[stepIndex].name);
    if (!alreadyAdded) {
      memorySpots.push(spots[stepIndex]);
      localStorage.setItem('memory_spots', JSON.stringify(memorySpots));
    }

    setToastMessage(`${spots[stepIndex].name} 도착!`);

    // Check if all visited
    if (newVisited.size === spots.length) {
      setTimeout(() => setShowCelebration(true), 1000);
    } else if (stepIndex < spots.length - 1) {
      // Auto-advance to next unvisited step
      setTimeout(() => {
        const nextUnvisited = findNextUnvisited(stepIndex, newVisited);
        setActiveStep(nextUnvisited);
      }, 1500);
    }
  };

  const handleUndoArrival = (stepIndex: number) => {
    const newVisited = new Set(visitedSteps);
    newVisited.delete(stepIndex);
    setVisitedSteps(newVisited);
    localStorage.setItem('travel_visited_steps', JSON.stringify([...newVisited]));

    // Remove from memory_spots
    const memorySpots = JSON.parse(localStorage.getItem('memory_spots') || '[]');
    const updated = memorySpots.filter((s: any) => s.name !== spots[stepIndex].name);
    localStorage.setItem('memory_spots', JSON.stringify(updated));

    setToastMessage('방문 기록이 취소되었습니다');
    setShowCelebration(false);
  };

  const findNextUnvisited = (fromIndex: number, visited: Set<number>) => {
    for (let i = fromIndex + 1; i < spots.length; i++) {
      if (!visited.has(i)) return i;
    }
    return fromIndex;
  };

  // ---- Navigation ----
  const nextStep = () => setActiveStep(prev => (prev < spots.length - 1 ? prev + 1 : prev));
  const prevStep = () => setActiveStep(prev => (prev > 0 ? prev - 1 : prev));

  // ---- Trip End Handler ----
  const handleEndTrip = async () => {
    const userId = localStorage.getItem('temp_user_id');
    const memorySpots = JSON.parse(localStorage.getItem('memory_spots') || '[]');
    const currentCourseMeta = JSON.parse(localStorage.getItem('current_course_meta') || '{}');

    // Create timeline if conditions met
    if (currentCourseMeta.course_id && memorySpots.length > 0) {
      try {
        const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/api\/?$/, '');
        const response = await fetch(`${API_URL}/api/journey/${currentCourseMeta.course_id}/create-timeline`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            userId: userId,
            memorySpots: memorySpots,
            tastingNotes: {}
          })
        });

        if (response.ok) {
          setToastMessage('타임라인이 생성되었습니다!');
          localStorage.removeItem('memory_spots');
        }
      } catch (e) {
        console.error("[TravelView] Failed to create timeline", e);
      }
    }

    // Cleanup travel state + course data (MapView가 깨끗한 지도를 보여주도록)
    localStorage.removeItem('travel_visited_steps');
    localStorage.removeItem('current_course');
    localStorage.removeItem('current_course_meta');
    localStorage.removeItem('all_courses');
    localStorage.removeItem('memory_spots');

    // Navigate to tasting-note
    router.push('/tasting-note');
  };

  // ---- My Location ----
  const handleMyLocation = () => {
    if (!navigator.geolocation) {
      setToastMessage("위치 정보를 사용할 수 없습니다.");
      return;
    }
    navigator.geolocation.getCurrentPosition((position) => {
      const { latitude, longitude } = position.coords;
      if (mapInstance.current && (window as any).Tmapv3) {
        const Tmapv3 = (window as any).Tmapv3;
        const newCenter = new Tmapv3.LatLng(latitude, longitude);
        mapInstance.current.setCenter(newCenter);

        new Tmapv3.Marker({
          position: newCenter,
          map: mapInstance.current,
          iconHTML: `<div style="width:20px; height:20px; background:#0066FF; border:3px solid white; border-radius:50%; box-shadow:0 4px 8px rgba(0,0,0,0.2), 0 0 0 8px rgba(0,102,255,0.15);"></div>`
        });
      }
    }, () => {
      setToastMessage("위치 정보를 가져올 수 없습니다.");
    });
  };

  // ---- Computed values ----
  const visitedCount = visitedSteps.size;
  const totalCount = spots.length;
  const progressPercent = totalCount > 0 ? (visitedCount / totalCount) * 100 : 0;
  const currentSpot = spots[activeStep] || null;
  const isCurrentVisited = visitedSteps.has(activeStep);
  const allVisited = visitedCount === totalCount && totalCount > 0;

  // ---- Render ----
  return (
    <div className="h-screen bg-gray-50 relative overflow-hidden font-['Inter']">

      {/* CSS for pulse animation */}
      <style jsx global>{`
        @keyframes travelPulse {
          0%, 100% { box-shadow: 0 4px 16px rgba(0,102,255,0.4), 0 0 0 8px rgba(0,102,255,0.15); }
          50% { box-shadow: 0 4px 20px rgba(0,102,255,0.6), 0 0 0 14px rgba(0,102,255,0.08); }
        }
        @keyframes confetti {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
        }
      `}</style>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[9999] animate-fade-in-down">
          <div className="bg-gray-900/90 backdrop-blur-md text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 border border-white/10">
            <Check size={18} className="text-[#00C853]" />
            <span className="text-sm font-bold">{toastMessage}</span>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MINIMAL HEADER */}
      {/* ============================================================ */}
      <header className="absolute top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-md shadow-sm">
        <div className="flex items-center justify-between px-5 py-4">
          {/* Back */}
          <button
            onClick={() => router.push('/map')}
            className="w-10 h-10 rounded-full bg-gray-50 flex items-center justify-center hover:bg-gray-100 active:scale-95 transition-all"
          >
            <ArrowLeft size={20} className="text-gray-700" />
          </button>

          {/* Title */}
          <div className="flex-1 mx-3 text-center">
            <h1 className="text-base font-black text-gray-900 truncate">
              {courseMeta?.course_name || '여행 코스'}
            </h1>
            <p className="text-[10px] font-bold text-[#0066FF] tracking-wider uppercase mt-0.5">
              Traveling
            </p>
          </div>

          {/* End Trip */}
          <button
            onClick={() => setShowEndConfirm(true)}
            className="px-3.5 py-2 rounded-full bg-gray-900 text-white text-xs font-black active:scale-95 transition-all shadow-lg"
          >
            여행 종료
          </button>
        </div>

        {/* Progress Bar */}
        <div className="h-1 bg-gray-100">
          <div
            className="h-full bg-gradient-to-r from-[#00C853] to-[#69F0AE] transition-all duration-700 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </header>

      {/* ============================================================ */}
      {/* MAP */}
      {/* ============================================================ */}
      <div
        ref={mapRef}
        id="travel_map_div"
        className="absolute inset-0 z-0 bg-[#E5E7EB]"
        style={{ height: "100vh" }}
      />

      {/* ============================================================ */}
      {/* FLOATING PROGRESS INDICATOR */}
      {/* ============================================================ */}
      <div className="absolute top-[76px] left-1/2 -translate-x-1/2 z-40">
        <div className="bg-white/95 backdrop-blur-md px-5 py-2.5 rounded-full shadow-lg border border-gray-100 flex items-center gap-3">
          {/* Step dots */}
          <div className="flex items-center gap-1.5">
            {spots.map((_, index) => {
              const isV = visitedSteps.has(index);
              const isC = index === activeStep;
              return (
                <button
                  key={index}
                  onClick={() => { setActiveStep(index); setSheetOpen(true); }}
                  className={`rounded-full transition-all duration-300 ${
                    isV
                      ? 'w-3 h-3 bg-[#00C853]'
                      : isC
                        ? 'w-4 h-4 bg-[#0066FF] ring-4 ring-blue-100'
                        : 'w-2.5 h-2.5 bg-gray-300'
                  }`}
                />
              );
            })}
          </div>

          {/* Count */}
          <div className="border-l border-gray-200 pl-3 flex items-center gap-1">
            <span className="text-sm font-black text-[#0066FF]">{visitedCount}</span>
            <span className="text-sm font-black text-gray-400">/</span>
            <span className="text-sm font-black text-gray-700">{totalCount}</span>
            <span className="text-[10px] text-gray-500 font-bold ml-0.5">방문</span>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* MY LOCATION BUTTON */}
      {/* ============================================================ */}
      <div className="absolute bottom-40 right-5 z-40">
        <button
          onClick={handleMyLocation}
          className="w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center text-gray-700 active:bg-gray-50 active:scale-95 transition-all border border-gray-100"
        >
          <Locate size={22} />
        </button>
      </div>

      {/* ============================================================ */}
      {/* BOTTOM SHEET */}
      {/* ============================================================ */}
      <MotionDiv
        drag="y"
        dragConstraints={{ top: 0, bottom: 0 }}
        dragElastic={0.1}
        onDragEnd={handleDragEnd}
        animate={controls}
        initial={{ height: OPEN_HEIGHT }}
        className="absolute bottom-0 left-0 right-0 bg-white shadow-[0_-20px_50px_rgba(0,0,0,0.1)] rounded-t-[2.5rem] z-[200] overflow-hidden"
      >
        {/* Drag Handle */}
        <div className="w-full pt-4 pb-2 cursor-grab active:cursor-grabbing flex justify-center touch-none">
          <div className="w-14 h-1.5 bg-gray-200 rounded-full" />
        </div>

        {currentSpot ? (
          <div className="px-6 flex flex-col h-full overflow-hidden">

            {/* ---- Collapsed View ---- */}
            {!sheetOpen ? (
              <div className="flex items-center justify-between py-2 animate-fade-in">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${isCurrentVisited ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-[#0066FF]'}`}>
                      {isCurrentVisited ? 'VISITED' : `STEP ${activeStep + 1}`}
                    </span>
                  </div>
                  <h2 className="text-lg font-black text-gray-900 truncate">{currentSpot.name}</h2>
                </div>
                <button
                  onClick={() => setSheetOpen(true)}
                  className="w-12 h-12 bg-[#0066FF] text-white rounded-2xl flex items-center justify-center shadow-lg shadow-blue-100 active:scale-95 transition-all shrink-0 ml-3"
                >
                  <Navigation2 size={20} fill="currentColor" />
                </button>
              </div>
            ) : (
              /* ---- Expanded View ---- */
              <div className="animate-fade-in flex flex-col h-full pb-6 overflow-y-auto custom-scrollbar">

                {/* Step label */}
                <div className="flex items-center gap-2 mb-3">
                  <span className={`text-[10px] font-black px-2.5 py-1 rounded-full tracking-wider uppercase ${
                    isCurrentVisited ? 'bg-green-50 text-green-600 border border-green-200' : 'bg-blue-50 text-[#0066FF] border border-blue-200'
                  }`}>
                    {isCurrentVisited ? 'Visited' : `Step ${activeStep + 1}`}
                  </span>
                  <span className="text-xs text-gray-300 font-bold">{activeStep + 1} / {totalCount}</span>
                </div>

                {/* Place Card */}
                <div className="flex gap-4 items-start mb-4">
                  <div className="w-20 h-20 rounded-2xl overflow-hidden shadow-sm shrink-0 border border-gray-100 bg-gray-50">
                    {currentSpot.img ? (
                      <img
                        src={currentSpot.img}
                        className="w-full h-full object-cover"
                        alt={currentSpot.name}
                        loading="lazy"
                        onError={(e) => {
                          const img = e.target as HTMLImageElement;
                          img.style.display = 'none';
                          if (img.parentElement) {
                            img.parentElement.innerHTML = '<div class="w-full h-full flex items-center justify-center text-2xl bg-gray-50">📍</div>';
                          }
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-2xl bg-gray-50">📍</div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-black text-gray-900 mb-1 break-words leading-tight">{currentSpot.name}</h3>
                    {currentSpot.address && (
                      <p className="text-xs text-gray-400 font-medium mb-1.5 truncate">{currentSpot.address}</p>
                    )}
                    <p className="text-xs text-gray-500 font-medium leading-relaxed line-clamp-2">{currentSpot.desc}</p>
                  </div>
                </div>

                {/* ---- ARRIVAL BUTTON ---- */}
                {isCurrentVisited ? (
                  <div className="mb-4">
                    <div className="w-full py-3.5 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-black text-sm rounded-2xl flex items-center justify-center gap-2 shadow-lg shadow-green-200">
                      <Check size={18} />
                      방문 완료
                    </div>
                    <button
                      onClick={() => handleUndoArrival(activeStep)}
                      className="w-full mt-2 py-2 text-xs font-bold text-gray-400 hover:text-red-400 transition-colors text-center"
                    >
                      방문 취소하기
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => handleArrival(activeStep)}
                    className="w-full py-4 bg-[#0066FF] text-white font-black text-sm rounded-2xl flex items-center justify-center gap-2 shadow-lg shadow-blue-200 active:scale-[0.98] transition-all mb-4 hover:bg-[#0055DD]"
                  >
                    <MapPin size={18} />
                    도착 완료!
                  </button>
                )}

                {/* ---- QUICK ACTIONS ---- */}
                <div className="flex gap-2 mb-4">
                  {/* Memory */}
                  <button
                    onClick={() => {
                      const memorySpots = JSON.parse(localStorage.getItem('memory_spots') || '[]');
                      const alreadyAdded = memorySpots.some((s: any) => s.name === currentSpot.name);
                      if (alreadyAdded) {
                        const updated = memorySpots.filter((s: any) => s.name !== currentSpot.name);
                        localStorage.setItem('memory_spots', JSON.stringify(updated));
                        setToastMessage('추억에서 제거했습니다');
                      } else {
                        memorySpots.push(currentSpot);
                        localStorage.setItem('memory_spots', JSON.stringify(memorySpots));
                        setToastMessage(`${currentSpot.name}을(를) 추억에 저장했습니다`);
                      }
                    }}
                    className="flex-1 py-3 bg-gradient-to-r from-pink-50 to-purple-50 border border-pink-200 rounded-xl flex items-center justify-center gap-1.5 text-xs font-bold text-pink-500 active:scale-95 transition-all"
                  >
                    <Camera size={14} />
                    추억 남기기
                  </button>

                  {/* Naver Map */}
                  <button
                    onClick={() => {
                      const url = `https://map.naver.com/v5/directions/-/${currentSpot.lng},${currentSpot.lat},${encodeURIComponent(currentSpot.name)}/-/car`;
                      window.open(url, '_blank');
                    }}
                    className="py-3 px-4 bg-white border border-gray-200 rounded-xl flex items-center justify-center gap-1.5 text-xs font-black text-[#03C75A] active:scale-95 transition-all"
                  >
                    <span className="text-sm font-black">N</span>
                    네이버
                  </button>

                  {/* Kakao Map */}
                  <button
                    onClick={() => {
                      const destName = encodeURIComponent(currentSpot.name.replace(/,/g, ' '));
                      const url = `https://map.kakao.com/link/to/${destName},${currentSpot.lat},${currentSpot.lng}`;
                      window.open(url, '_blank');
                    }}
                    className="py-3 px-4 bg-[#FEE500] border border-yellow-300 rounded-xl flex items-center justify-center gap-1.5 text-xs font-black text-[#1952C5] active:scale-95 transition-all"
                  >
                    <span className="text-sm font-black">K</span>
                    카카오
                  </button>
                </div>

                {/* ---- PREV / NEXT NAVIGATION ---- */}
                <div className="flex gap-3">
                  <button
                    onClick={prevStep}
                    disabled={activeStep === 0}
                    className="flex-1 py-3.5 bg-gray-50 text-gray-500 rounded-2xl font-black text-sm disabled:opacity-30 active:scale-95 transition-all flex items-center justify-center gap-1.5"
                  >
                    <ChevronLeft size={16} />
                    이전
                  </button>

                  {allVisited ? (
                    <button
                      onClick={() => setShowEndConfirm(true)}
                      className="flex-1 py-3.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-2xl font-black text-sm active:scale-95 transition-all shadow-lg shadow-blue-200 flex items-center justify-center gap-1.5"
                    >
                      여행 마무리하기
                    </button>
                  ) : (
                    <button
                      onClick={nextStep}
                      disabled={activeStep === spots.length - 1}
                      className="flex-1 py-3.5 bg-gray-100 text-gray-800 rounded-2xl font-black text-sm disabled:opacity-30 active:scale-95 transition-all flex items-center justify-center gap-1.5"
                    >
                      다음
                      <ChevronRight size={16} />
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-gray-400 font-bold">
            코스 정보를 불러오는 중...
          </div>
        )}
      </MotionDiv>

      {/* ============================================================ */}
      {/* END TRIP CONFIRMATION MODAL */}
      {/* ============================================================ */}
      {showEndConfirm && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowEndConfirm(false)} />
          <div className="relative bg-white rounded-3xl shadow-2xl p-8 mx-6 max-w-sm w-full animate-scale-in">
            <div className="text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🏁</span>
              </div>
              <h3 className="text-xl font-black text-gray-900 mb-2">여행을 종료할까요?</h3>
              <p className="text-sm text-gray-500 font-medium mb-1">
                방문한 장소: <span className="font-black text-[#00C853]">{visitedCount}</span> / {totalCount}곳
              </p>
              {visitedCount < totalCount && (
                <p className="text-xs text-orange-400 font-bold mb-4">
                  아직 방문하지 않은 장소가 {totalCount - visitedCount}곳 있어요
                </p>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowEndConfirm(false)}
                className="flex-1 py-3.5 bg-gray-100 text-gray-600 rounded-2xl font-bold text-sm active:scale-95 transition-all"
              >
                계속 여행
              </button>
              <button
                onClick={() => {
                  setShowEndConfirm(false);
                  handleEndTrip();
                }}
                className="flex-1 py-3.5 bg-gray-900 text-white rounded-2xl font-bold text-sm active:scale-95 transition-all shadow-lg"
              >
                종료하기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* ALL VISITED CELEBRATION */}
      {/* ============================================================ */}
      {showCelebration && (
        <div className="fixed inset-0 z-[9998] flex items-center justify-center animate-fade-in">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowCelebration(false)} />
          <div className="relative bg-white rounded-3xl shadow-2xl p-8 mx-6 max-w-sm w-full animate-scale-in text-center">
            <div className="text-6xl mb-4">🎉</div>
            <h3 className="text-2xl font-black text-gray-900 mb-2">모든 장소를 방문했어요!</h3>
            <p className="text-sm text-gray-500 font-medium mb-6">
              광주 여행이 완성되었습니다.<br />
              추억을 마무리해 볼까요?
            </p>

            <div className="flex flex-col gap-3">
              <button
                onClick={() => {
                  setShowCelebration(false);
                  handleEndTrip();
                }}
                className="w-full py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-2xl font-black text-sm active:scale-95 transition-all shadow-lg shadow-blue-200 flex items-center justify-center gap-2"
              >
                <Camera size={18} />
                여행 마무리하기
              </button>
              <button
                onClick={() => setShowCelebration(false)}
                className="w-full py-3 text-gray-400 font-bold text-xs active:scale-95 transition-all"
              >
                조금 더 둘러보기
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
