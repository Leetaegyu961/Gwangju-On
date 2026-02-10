import type { Metadata } from "next";
import invitationCoursesData from '../../../data/invitation_courses.json';

const COURSE_IMAGES: Record<string, string> = {
    "course-1": "https://images.unsplash.com/photo-1534234828563-025816976a44?w=800&q=80",
    "course-2": "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800&q=80",
    "course-3": "https://images.unsplash.com/photo-1596436889106-be35c843f974?w=800&q=80",
    "course-4": "https://images.unsplash.com/photo-1566127444979-b3d2b654e3d7?w=800&q=80",
    "course-5": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80",
    "course-6": "https://images.unsplash.com/photo-1627740924089-a29d89299403?w=800&q=80",
    "course-7": "https://images.unsplash.com/photo-1506161986422-48df74ce0076?w=800&q=80",
};

type Props = {
    params: Promise<{ courseId: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { courseId } = await params;
    const course = invitationCoursesData.find((c: any) => c.id === courseId);

    if (!course) {
        return {
            title: "광주 ON | 여행 초대장",
            description: "AI가 추천하는 광주 여행 코스",
        };
    }

    const placesPreview = course.places.map((p: any) => p.name).join(' → ');

    return {
        title: `광주ON - ${course.title}`,
        description: `${course.description}\n${placesPreview}`,
        openGraph: {
            title: `여행 초대장이 도착했어요! - ${course.title}`,
            description: `${course.description}\n📍 ${placesPreview}`,
            images: [COURSE_IMAGES[courseId] || "https://placehold.co/1200x630/0066FF/FFFFFF/png?text=Gwangju+On"],
            type: "website",
            siteName: "광주 ON | AI Travel Curator",
        },
        twitter: {
            card: "summary_large_image",
            title: `광주ON - ${course.title}`,
            description: course.description,
            images: [COURSE_IMAGES[courseId] || "https://placehold.co/1200x630/0066FF/FFFFFF/png?text=Gwangju+On"],
        },
    };
}

export default function InviteLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
