"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { InvitationPopup } from '../../../features/experience/InvitationPopup';
import invitationCoursesData from '../../../data/invitation_courses.json';
import { getCourseImage } from '../../../utils/courseImages';

const COURSE_IMAGES: Record<string, string> = {
    "course-1": "https://images.unsplash.com/photo-1534234828563-025816976a44?w=800&q=80",
    "course-2": "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800&q=80",
    "course-3": "https://images.unsplash.com/photo-1596436889106-be35c843f974?w=800&q=80",
    "course-4": "https://images.unsplash.com/photo-1566127444979-b3d2b654e3d7?w=800&q=80",
    "course-5": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80",
    "course-6": "https://images.unsplash.com/photo-1627740924089-a29d89299403?w=800&q=80",
    "course-7": "https://images.unsplash.com/photo-1506161986422-48df74ce0076?w=800&q=80",
};

export default function InvitePage() {
    const params = useParams();
    const courseId = params.courseId as string;
    const [invitationData, setInvitationData] = useState<any>(null);

    useEffect(() => {
        const course = invitationCoursesData.find((c: any) => c.id === courseId);
        if (course) {
            setInvitationData({
                id: course.id,
                title: course.title,
                description: course.description,
                imageUrl: COURSE_IMAGES[courseId] || "https://placehold.co/800x450/0066FF/FFFFFF/png?text=Gwangju+On",
                places: course.places.map((p: any) => ({
                    ...p,
                    imageUrl: p.img || getCourseImage([p.type || "여행"], p.name)
                }))
            });
        }
    }, [courseId]);

    if (!invitationData) {
        return (
            <div className="h-screen bg-gradient-to-b from-[#0066FF] to-blue-800 flex items-center justify-center">
                <div className="text-center text-white space-y-4">
                    <div className="text-6xl">🗺️</div>
                    <h1 className="text-2xl font-black">광주 ON</h1>
                    <p className="text-white/70 text-sm">초대장을 불러오는 중...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen bg-gradient-to-b from-[#0066FF] to-blue-800 flex items-center justify-center relative">
            {/* 배경 장식 */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-20 left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl" />
                <div className="absolute bottom-40 right-10 w-48 h-48 bg-white/5 rounded-full blur-3xl" />
            </div>

            <InvitationPopup
                isOpen={true}
                onClose={() => {
                    window.location.href = '/survey';
                }}
                invitationData={invitationData}
            />
        </div>
    );
}
