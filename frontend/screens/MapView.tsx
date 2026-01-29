"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Navigation2, ArrowLeft, Locate } from 'lucide-react';
import Script from 'next/script';
import { motion, useAnimation, PanInfo } from 'framer-motion';

export const MapView = () => {
  const router = useRouter();

  // --------------------------------------------------------------------------
  // 1. References (Ref) & State 정의
  // --------------------------------------------------------------------------

  // 지도 DOM 및 인스턴스 참조
  const mapRef = useRef<HTMLDivElement>(null); // 지도가 그려질 DOM 엘리먼트
  const mapInstance = useRef<any>(null);      // Tmap 인스턴스 객체

  // 마커 및 경로 객체 관리 (지도에서 제거/추가를 위해 저장)
  const markersRef = useRef<any[]>([]);       // 현재 표시된 마커들
  const polylinesRef = useRef<any[]>([]);     // 경로(선) 객체들

  // 상세정보 검색 취소용 컨트롤러 (중복 요청 방지 및 취소 처리)
  const abortControllerRef = useRef<AbortController | null>(null);

  // UI 상태 관리
  const [activeStep, setActiveStep] = useState(0);    // 코스 모드에서 현재 선택된 단계 (Index)
  const [sheetOpen, setSheetOpen] = useState(true);   // 하단 바텀 시트 열림/닫힘 상태
  const [spots, setSpots] = useState<any[]>([]);      // 여행 코스 데이터 (localStorage에서 로드)

  // 지도 및 로딩 상태
  const [isMapReady, setIsMapReady] = useState(false);      // Tmap 로드 완료 여부
  const [isLoadingRoute, setIsLoadingRoute] = useState(false); // 경로 탐색(도보/차량) 로딩 중 여부

  // 뷰 모드 및 검색 상태
  const [viewMode, setViewMode] = useState<'places' | 'course'>('places'); // 'places'(장소검색) vs 'course'(코스안내)
  const [activeCategory, setActiveCategory] = useState('전체'); // 현재 선택된 장소 카테고리 (맛집, 카페 등)
  const [allPlaces, setAllPlaces] = useState<any[]>([]);    // Tmap API로 검색된 장소 목록

  // 상세 정보 상태
  const [selectedPlace, setSelectedPlace] = useState<{ name: string, content: string, img?: string } | null>(null); // 선택된 장소의 상세 정보
  const [isDetailLoading, setIsDetailLoading] = useState(false); // AI 상세 정보 로딩 중 여부
  const [isSearching, setIsSearching] = useState(false);       // 장소 검색(POI) 로딩 중 여부

  // 기타 UI 상태
  const [isRouteOptionsOpen, setIsRouteOptionsOpen] = useState(false); // 경로 옵션 토글 상태
  const controls = useAnimation(); // Framer Motion 애니메이션 제어

  // --------------------------------------------------------------------------
  // 2. Event Listener용 State 참조 (Ref 동기화)
  // Tmap 이벤트 리스너 내부에서 최신 State 값을 참조하기 위해 Ref 사용
  // --------------------------------------------------------------------------
  const activeCategoryRef = useRef(activeCategory);
  useEffect(() => { activeCategoryRef.current = activeCategory; }, [activeCategory]);

  const viewModeRef = useRef(viewMode);
  useEffect(() => { viewModeRef.current = viewMode; }, [viewMode]);

  const sheetOpenRef = useRef(sheetOpen);
  useEffect(() => { sheetOpenRef.current = sheetOpen; }, [sheetOpen]);

  // Tmap POI Search Function
  const searchPlaces = async () => {
    if (!mapInstance.current || !(window as any).Tmapv3) return;

    const Tmapv3 = (window as any).Tmapv3;
    const center = mapInstance.current.getCenter();
    const API_BASE_URL = "http://localhost:8000";

    // 현재 요청하는 카테고리 캡처
    const targetCategory = activeCategoryRef.current;

    // 검색 키워드 정의
    const keywordMap: { [key: string]: string } = {
      '맛집': '음식점', // "맛집"보다 "음식점"이 더 포괄적이고 정확할 수 있음
      '카페': '카페',
      '관광': '관광명소'
    };

    let keywordsToSearch: string[] = [];
    if (targetCategory === '전체') {
      keywordsToSearch = ['음식점', '카페', '관광명소'];
    } else {
      keywordsToSearch = [keywordMap[targetCategory] || targetCategory];
    }

    try {
      setIsSearching(true); // 로딩 시작

      // 병렬 요청으로 여러 카테고리 동시 검색 (전체일 경우)
      const requests = keywordsToSearch.map(k =>
        fetch(`${API_BASE_URL}/api/tmap/poi/around?keyword=${encodeURIComponent(k)}&lat=${center.lat()}&lng=${center.lng()}&radius=3&count=${targetCategory === '전체' ? 10 : 20}`)
          .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
          })
          .then(data => ({ keyword: k, data }))
      );

      const results = await Promise.all(requests);

      // 🚨 중요: 응답을 받았을 때, 사용자가 이미 다른 카테고리를 눌렀다면 이 결과는 버림
      if (activeCategoryRef.current !== targetCategory) {
        console.log(`🚫 [MapView] Ignored old result for ${targetCategory} (Current: ${activeCategoryRef.current})`);
        return;
      }

      let mergedPois: any[] = [];

      results.forEach(({ keyword, data }) => {
        if (data.searchPoiInfo?.pois?.poi) {
          // 키워드를 원래 카테고리명으로 매핑 (UI 표시용)
          let catLabel = targetCategory;
          if (targetCategory === '전체') {
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

      // "주차장" 포함된 장소 필터링
      const filteredPois = uniquePois.filter(p => !p.name.includes("주차장"));

      console.log(`📍 [MapView] Found ${filteredPois.length} places (Category: ${targetCategory})`);

      if (filteredPois.length === 0) {
        console.warn("⚠️ [MapView] No POI found");
      }
      setAllPlaces(filteredPois);

    } catch (err) {
      console.error("❌ [MapView] POI Search Error", err);
    } finally {
      setIsSearching(false); // 로딩 끝
    }
  };

  // Fetch place detail from Agent
  // --------------------------------------------------------------------------
  // 3. AI 상세 정보 조회 (Agent 연동)
  // --------------------------------------------------------------------------
  const fetchPlaceDetail = async (name: string, address: string = "") => {
    // [중복 요청 방지 로직]
    // 1. 이전 요청이 진행 중이라면 취소(abort)시킵니다.
    // 2. 창을 닫거나 다른 마커를 눌렀을 때, 이전 마커의 정보가 늦게 뜨는 것을 방지합니다.
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsDetailLoading(true);
    setSelectedPlace({ name, content: "" }); // 내용 초기화

    // [주소 컨텍스트 추출]
    // AI에게 더 정확한 정보를 요청하기 위해 주소에서 '동(Dong)' 정보를 추출합니다.
    let locationContext = "광주에 있는";
    if (address) {
      const parts = address.split(" ");
      const dong = parts.find(p => p.endsWith("동") || p.endsWith("가") || p.endsWith("로"));
      if (dong) {
        locationContext = `${dong}에 있는`;
      }
    }

    try {
      // AI Backend에 질문 전송
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `${locationContext} ${name}에 대해 간단히 소개해줘. 특징 1가지와 방문객 리뷰 핵심 1가지만 짧은 개조식(bullet point)으로 알려줘.`,
          userId: "user_map_view"
        }),
        signal: controller.signal // AbortController Signal 연결
      });

      if (!response.ok) throw new Error('Failed to fetch detail');

      const data = await response.json();

      // 요청이 취소된 상태라면 결과 무시
      if (controller.signal.aborted) return;

      // 이미지 데이터 추출 (EvidenceCards 활용)
      let imgUrl = undefined;
      if (data.evidenceCards && data.evidenceCards.length > 0) {
        imgUrl = data.evidenceCards[0].img;
      }

      // 상태 업데이트 (UI에 상세 정보 표시)
      setSelectedPlace({ name, content: data.text, img: imgUrl });
    } catch (e: any) {
      if (e.name === 'AbortError') {
        console.log("🚫 [MapView] Detail fetch aborted");
        return;
      }
      console.error("❌ [MapView] Detail fetch error", e);
      setSelectedPlace({ name, content: "정보를 불러오는 데 실패했어요." });
    } finally {
      // 현재 완료된 요청이 마지막 요청과 일치할 때만 로딩 종료
      if (abortControllerRef.current === controller) {
        setIsDetailLoading(false);
        abortControllerRef.current = null;
      }
    }
  };

  // --------------------------------------------------------------------------
  // 4. Global Event Handlers for Markers
  // Tmap Marker는 HTML 문자열로 주입되므로, React 함수에 직접 접근할 수 없습니다.
  // 따라서 window 객체에 전역 함수를 할당하여 HTML onclick 이벤트와 연결합니다.
  // --------------------------------------------------------------------------
  useEffect(() => {
    // 마커 내부의 "상세정보 보기" 버튼 클릭 시 실행될 함수
    (window as any).handlePlaceDetail = (name: string, addr: string) => fetchPlaceDetail(name, addr);

    // 마커 아이콘 클릭 시 실행될 토글 함수
    // - 클릭한 마커의 상세정보 버튼만 보이게 하고 나머지는 숨김
    (window as any).toggleDetailBtn = (id: string) => {
      const el = document.getElementById(id);
      if (el) {
        // 다른 열린 버튼들은 닫기 (하나만 열리게)
        document.querySelectorAll('.detail-btn-custom').forEach((b: any) => {
          if (b.id !== id) b.style.display = 'none';
        });
        // 현재 버튼 토글 (Show/Hide)
        el.style.display = el.style.display === 'none' ? 'block' : 'none';
      }
    };
  }, [fetchPlaceDetail]);

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

  // --------------------------------------------------------------------------
  // 5. Tmap 초기화 (최초 1회 실행)
  // --------------------------------------------------------------------------
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

    // [초기 중심 좌표 설정]
    // 첫 번째 장소 위치로 설정하거나, 데이터가 없으면 광주 시청 좌표를 기본값으로 사용
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

    // [지도 객체 생성]
    mapInstance.current = new Tmapv3.Map(mapRef.current, {
      center: new Tmapv3.LatLng(initialLat, initialLng),
      width: "100%",
      height: "100%",
      zoom: 15, // 초기 줌 레벨 (조금 더 확대)
      zoomControl: false, // 줌 컨트롤 숨김 (깔끔한 UI)
    });

    console.log("✅ [MapView] Map instance created");
    setIsMapReady(true);

    // [지도 빈 공간 클릭 이벤트 핸들러]
    // 지도 배경을 클릭했을 때, 활성화된 UI 요소들을 닫는 역할
    mapInstance.current.on("Click", () => {
      // 1. 장소 모드: 열려있는 모든 상세정보 버튼 닫기 (초기화)
      if (viewModeRef.current === 'places') {
        document.querySelectorAll('.detail-btn-custom').forEach((b: any) => {
          b.style.display = 'none';
        });
      }

      // 2. 코스 모드: 하단 바텀 시트 닫기 및 상세 내역 리셋
      if (viewModeRef.current === 'course') {
        if (sheetOpenRef.current) {
          setSheetOpen(false);
        }
        // AI 상세정보 요청이 진행 중이었다면 취소
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }
        setIsDetailLoading(false);
        setSelectedPlace(null);
      }
    });

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
          : `<div class="group" style="display:flex; flex-direction:column; align-items:center; width:120px; transform:translate(-50%, -50%); pointer-events:none;">
               <div onclick="window.toggleDetailBtn('marker-detail-btn-${index}'); event.stopPropagation();" 
                    style="background:${markerBg}; color:${markerBorder}; padding:6px; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; border:2px solid ${markerBorder}; box-shadow: 0 4px 12px rgba(0,0,0,0.1); font-size:16px; cursor: pointer; pointer-events: auto;">${markerIcon}</div>
               <span style="background:white; margin-top:4px; padding:3px 8px; border-radius:8px; border:1px solid #eee; font-size:11px; font-weight:bold; color:#333; box-shadow:0 2px 4px rgba(0,0,0,0.05); white-space:nowrap; max-width:100%; overflow:hidden; text-overflow:ellipsis; pointer-events:none;">${spot.name}</span>
               <button 
                 id="marker-detail-btn-${index}"
                 class="detail-btn-custom"
                 onclick="window.handlePlaceDetail('${spot.name.replace(/'/g, "\\'")}', '${(spot.address || "").replace(/'/g, "\\'")}')"
                 style="display:none; absolute; top:36px; background:black; color:white; margin-top:4px; padding:4px 10px; border-radius:8px; border:none; font-size:11px; font-weight:bold; cursor:pointer; pointer-events:auto; box-shadow:0 4px 8px rgba(0,0,0,0.2); z-index:9999;">
                 상세정보 👉
               </button>
             </div>`;

        const marker = new Tmapv3.Marker({
          position: position,
          map: mapInstance.current,
          iconHTML: markerContent,
          // title: spot.name // title 제거, 라벨로 대체
        });

        // Marker Click Event
        const onMarkerClick = () => {
          if (viewMode === 'course') {
            // 코스 모드일 때는 해당 단계의 카드를 보여줌 (AI 검색 X)
            setActiveStep(index);
            setSelectedPlace(null);
            setSheetOpen(true);
          }
          // 장소 모드일 때는 마커 클릭 시 아무 동작 안함 (버튼 클릭으로 처리)
        };

        if (marker.on) {
          marker.on("Click", onMarkerClick);
          marker.on("click", onMarkerClick);
        } else if (marker.addListener) {
          marker.addListener("click", onMarkerClick);
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

      if (displayData.length > 0) {
        // 마커 렌더링 후 지도 범위 재설정 (약간의 지연 필요)
        setTimeout(() => {
          if (mapInstance.current) {
            mapInstance.current.fitBounds(bounds);

            // fitBounds 직후 panBy가 무시되는 경우를 방지하기 위해 2차 지연
            setTimeout(() => {
              const yOffset = viewMode === 'course' ? -120 : -60;
              mapInstance.current.panBy(0, yOffset);
            }, 100);
          }
        }, 200);
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
      // 즉시 요청 취소 및 로딩 해제
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setIsDetailLoading(false);

      // 창을 내리면 상세 정보 및 로딩 상태 초기화
      setTimeout(() => {
        setSelectedPlace(null);
      }, 200); // 애니메이션 자연스럽게 연결
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

        {viewMode === 'places' && (
          <div className="px-6 py-4 flex gap-2 overflow-x-auto no-scrollbar bg-gray-50/50">
            {['전체', '맛집', '카페', '관광'].map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  setActiveCategory(cat);
                  setViewMode('places'); // 카테고리 클릭 시 장소 모드로 전환
                  setAllPlaces([]); // 이전 결과 즉시 삭제 (화면 초기화)
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
        )}
      </header>

      {isSearching && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center pointer-events-none">
          <div className="bg-white/90 backdrop-blur-md px-6 py-4 rounded-2xl shadow-xl flex flex-col items-center gap-3 border border-gray-100 animate-fade-in">
            <div className="w-8 h-8 border-4 border-[#0066FF] border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs font-bold text-gray-600">장소를 찾고 있어요...</span>
          </div>
        </div>
      )}

      <div className="absolute top-[180px] left-1/2 -translate-x-1/2 z-40">
        {viewMode === 'places' && (
          <button
            onClick={searchPlaces}
            className="bg-white/90 backdrop-blur-md px-6 py-2.5 rounded-full shadow-2xl border border-white/50 text-[#0066FF] font-black text-sm flex items-center gap-2 active:scale-95 transition-all">
            <span className="animate-spin-slow text-lg">🔄</span>
            현 지도에서 검색
          </button>
        )}
      </div>

      {/* 내 위치 버튼 */}
      <div className="absolute bottom-48 right-5 z-40">
        <button
          onClick={() => {
            if (!navigator.geolocation) {
              alert("위치 정보를 사용할 수 없습니다.");
              return;
            }
            setIsSearching(true);
            navigator.geolocation.getCurrentPosition((position) => {
              const { latitude, longitude } = position.coords;
              if (mapInstance.current && (window as any).Tmapv3) {
                const Tmapv3 = (window as any).Tmapv3;
                const newCenter = new Tmapv3.LatLng(latitude, longitude);
                mapInstance.current.setCenter(newCenter);

                // 내 위치 표시 마커 (파란 점)
                new Tmapv3.Marker({
                  position: newCenter,
                  map: mapInstance.current,
                  iconHTML: `<div style="width:20px; height:20px; background:#0066FF; border:3px solid white; border-radius:50%; box-shadow:0 4px 8px rgba(0,0,0,0.2);"></div>`
                });
              }
              setIsSearching(false);
            }, () => {
              alert("위치 정보를 가져올 수 없습니다.");
              setIsSearching(false);
            });
          }}
          className="w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center text-gray-700 active:bg-gray-50 active:scale-95 transition-all"
        >
          <Locate size={24} />
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
                      if (abortControllerRef.current) {
                        abortControllerRef.current.abort();
                        abortControllerRef.current = null;
                      }
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
                {/* 경로 모드 선택 버튼 (도보 안내 vs 외부 길찾기) */}
                <div className="flex gap-3 mt-4">
                  {/* 1. 도보 안내 (앱 내 Tmap) */}
                  <button
                    onClick={() => fetchRoute('pedestrian')}
                    disabled={isLoadingRoute || activeStep >= spots.length - 1}
                    className={`flex-1 py-3 rounded-2xl font-black text-sm transition-all flex flex-col items-center justify-center gap-1 shadow-sm border ${routeMode === 'pedestrian'
                      ? 'bg-[#0066FF] text-white border-[#0066FF]'
                      : 'bg-white text-gray-700 border-gray-200'
                      }`}
                  >
                    <span className="flex items-center gap-1.5"><span className="text-lg">🚶</span> 도보 안내</span>
                    {totalTime > 0 && routeMode === 'pedestrian' && <span className="text-[10px] opacity-90 font-bold">{formatTime(totalTime)}</span>}
                  </button>

                  {/* 2. 외부 길찾기 (네이버/카카오) */}
                  <div className="flex-1 bg-gray-50 rounded-2xl border border-gray-100 px-4 py-2 flex flex-row items-center justify-center gap-4">
                    <span className="text-sm font-black text-gray-800 flex items-center gap-1 shrink-0">🗺️ 길찾기</span>
                    <div className="flex gap-3">
                      {/* 네이버 지도 아이콘 */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          // 현재 보고 있는 장소를 목적지로 설정 (출발지는 네이버 지도에서 내 위치로 자동 설정)
                          const dest = spots[activeStep];
                          const url = `https://map.naver.com/v5/directions/-/${dest.lng},${dest.lat},${encodeURIComponent(dest.name)}/-/car`;
                          window.open(url, '_blank');
                        }}
                        className="w-10 h-10 bg-white rounded-xl shadow-sm border border-gray-100 flex items-center justify-center hover:scale-110 transition-transform overflow-hidden relative group shrink-0"
                        title="네이버 지도로 길찾기"
                      >
                        {/* 네이버 지도 로고 스타일 */}
                        <div className="w-full h-full bg-[#03C75A] flex items-center justify-center text-white font-black text-xs">
                          N
                        </div>
                      </button>

                      {/* 카카오맵 아이콘 */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          // 현재 보고 있는 장소를 목적지로 설정
                          const dest = spots[activeStep];
                          const destName = encodeURIComponent(dest.name.replace(/,/g, ' '));
                          const url = `https://map.kakao.com/link/to/${destName},${dest.lat},${dest.lng}`;
                          window.open(url, '_blank');
                        }}
                        className="w-10 h-10 bg-[#FEE500] rounded-xl shadow-sm border border-gray-100 flex items-center justify-center hover:scale-110 transition-transform overflow-hidden group shrink-0"
                        title="카카오맵으로 길찾기"
                      >
                        {/* 카카오맵 핀 아이콘 (파란색 핀) */}
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M12 2C7.58172 2 4 5.58172 4 10C4 14.4183 12 22 12 22C12 22 20 14.4183 20 10C20 5.58172 16.4183 2 12 2Z" fill="#1952C5" />
                          <circle cx="12" cy="10" r="3" fill="white" />
                        </svg>
                      </button>
                    </div>
                  </div>
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
    </div >
  );
};
