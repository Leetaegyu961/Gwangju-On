"use client";

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { PlaceInteractiveCard } from '../../features/experience/PlaceInteractiveCard';
import { SummarySequence } from '../../features/experience/SummarySequence';
import { getCourseImage } from '../../utils/courseImages';

const allCourses = {
    'course-1': [
        { id: 'c1-1', name: "송정골", imageUrl: getCourseImage(["맛집"], "송정골"), description: "합리적인 가격의 굴비정식으로 유명한 로컬 맛집입니다.", category: "맛집", lat: 35.137, lng: 126.791 },
        { id: 'c1-2', name: "국립아시아문화전당", imageUrl: getCourseImage(["문화"], "국립아시아문화전당"), description: "명실상부한 아시아 문화예술의 거점 시설입니다.", category: "문화", lat: 35.148, lng: 126.920 },
        { id: 'c1-3', name: "동명동 카페거리", imageUrl: getCourseImage(["카페"], "동명동 카페거리"), description: "개성 있는 인테리어와 맛을 추구하는 카페들이 밀집한 거리입니다.", category: "카페", lat: 35.150, lng: 126.912 },
        { id: 'c1-4', name: "이이남스튜디오", imageUrl: getCourseImage(["예술"], "이이남스튜디오"), description: "세계적인 미디어아티스트 이이남 작가의 복합문화공간입니다.", category: "예술", lat: 35.145, lng: 126.915 }
    ],
    'course-2': [
        { id: 'c2-1', name: "광주호 호수생태원", imageUrl: getCourseImage(["자연"], "광주호 호수생태원"), description: "자연학습장과 수변 습지가 조성된 시민들의 휴식공간입니다.", category: "자연", lat: 35.184, lng: 127.000 },
        { id: 'c2-2', name: "광주 예술의 거리", imageUrl: getCourseImage(["예술"], "광주 예술의 거리"), description: "호남 예술의 진수를 접할 수 있는 전통문화 명소입니다.", category: "예술", lat: 35.151, lng: 126.917 },
        { id: 'c2-3', name: "제일반점", imageUrl: getCourseImage(["맛집"], "제일반점"), description: "50여 년 전통을 자랑하는 옛날식 자장면 전문 중식당입니다.", category: "맛집", lat: 35.152, lng: 126.918 },
        { id: 'c2-4', name: "금남로", imageUrl: getCourseImage(["역사"], "금남로"), description: "광주의 중추 기능과 5.18의 역사가 살아있는 상징적인 거리입니다.", category: "역사", lat: 35.153, lng: 126.919 }
    ],
    'course-3': [
        { id: 'c3-1', name: "만귀정", imageUrl: getCourseImage(["역사"], "만귀정"), description: "큰 연못 가운데 세워진 수중 정자로 광주광역시 문화재자료입니다.", category: "역사", lat: 35.132, lng: 126.835 },
        { id: 'c3-2', name: "운천사마애여래좌상", imageUrl: getCourseImage(["문화"], "운천사마애여래좌상"), description: "자연 암벽에 조각된 거대한 불상으로 웅장함을 자아냅니다.", category: "문화", lat: 35.150, lng: 126.855 },
        { id: 'c3-3', name: "5·18 기념공원", imageUrl: getCourseImage(["역사"], "5·18 기념공원"), description: "5.18의 교훈을 계승하기 위해 조성된 도심 속 생태공원입니다.", category: "역사", lat: 35.156, lng: 126.858 },
        { id: 'c3-4', name: "양동시장", imageUrl: getCourseImage(["시장"], "양동시장"), description: "100년 이상의 역사를 가진 호남 최대 규모의 전통시장입니다.", category: "시장", lat: 35.151, lng: 126.905 }
    ]
};

export default function DiscoveryPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [mode, setMode] = useState<'discovery' | 'summary'>('discovery');
    const [currentCourseId, setCurrentCourseId] = useState<'course-1' | 'course-2' | 'course-3'>('course-1');
    const [currentIndex, setCurrentIndex] = useState(0);
    const [pickedPlaces, setPickedPlaces] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const init = async () => {
            const sharedUserId = searchParams.get('shared');
            if (sharedUserId) {
                try {
                    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
                    const res = await fetch(`${API_URL}/journey/session/${sharedUserId}`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.album_data) {
                            setPickedPlaces(data.album_data);
                            setMode('summary');
                            setIsLoading(false);
                            return;
                        }
                    }
                } catch (e) {
                    console.error("Shared session load failed", e);
                }
            }

            const invitation = localStorage.getItem('pending_invitation');
            const invitationId = invitation ? JSON.parse(invitation).id : 'course-1';
            setCurrentCourseId(invitationId as any);
            setIsLoading(false);
        };
        init();
    }, [searchParams]);

    const handlePick = async (place: any) => {
        // 사일런트 데이터 로깅 (담기 이력 기록)
        try {
            const userId = localStorage.getItem('access_token') || localStorage.getItem('temp_user_id') || 'guest';
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
            await fetch(`${API_URL}/journey/log-action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userId,
                    actionType: 'PICK_PLACE',
                    data: { placeId: place.id, name: place.name }
                })
            });
        } catch (e) { console.error(e); }

        setPickedPlaces(prev => [...prev, place]);
        if (currentIndex < 3) { // 4개 장소 중 마지막이 아니면
            setCurrentIndex(prev => prev + 1);
        } else {
            handleFinish([...pickedPlaces, place]);
        }
    };

    const handleSkip = async () => {
        // 사일런트 데이터 로깅 (물색 이력 기록)
        try {
            const userId = localStorage.getItem('access_token') || localStorage.getItem('temp_user_id') || 'guest';
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
            await fetch(`${API_URL}/journey/log-action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userId,
                    actionType: 'SKIP_PLACE',
                    data: { currentCourseId, currentIndex }
                })
            });
        } catch (e) { console.error(e); }

        // C1 -> C2 -> C3 -> C1 순환 (동일 인덱스 유지)
        const courseIds: Array<keyof typeof allCourses> = ['course-1', 'course-2', 'course-3'];
        const nextIdx = (courseIds.indexOf(currentCourseId) + 1) % courseIds.length;
        setCurrentCourseId(courseIds[nextIdx]);
    };

    const handleFinish = async (finalPlaces: any[]) => {
        localStorage.setItem('current_course', JSON.stringify(finalPlaces));
        setMode('summary');

        const userId = localStorage.getItem('user_id') || localStorage.getItem('temp_user_id');
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
        await fetch(`${API_URL}/journey/status?user_id=${userId}&status=COMPLETED`, { method: 'POST' });
    };

    if (isLoading) return <div className="min-h-screen flex items-center justify-center bg-white"><p className="font-bold text-gray-400 text-sm">로드 중...</p></div>;

    const currentPlaces = allCourses[currentCourseId];

    return (
        <div className="bg-white min-h-screen flex flex-col items-center">
            {mode === 'discovery' ? (
                <div className="w-full max-w-[480px] h-full relative">
                    <PlaceInteractiveCard
                        places={currentPlaces}
                        currentIndex={currentIndex} // index 제어권 이관
                        onPick={handlePick}
                        onSkip={handleSkip}
                        onFinish={() => { }}
                    />
                </div>
            ) : (
                <SummarySequence
                    pickedPlaces={pickedPlaces}
                />
            )}
        </div>
    );
}
