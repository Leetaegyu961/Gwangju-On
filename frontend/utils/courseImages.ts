
// 여행 장소 카테고리별 고품질 이미지 매핑 유틸리티
// 실제 프로젝트에서는 CDN이나 더 많은 이미지 리스트를 활용할 수 있습니다.

// 키워드별 이미지 URL 리스트 (Updated Unsplash Source)
const PLACE_IMAGES: Record<string, string[]> = {
    cafe: [
        'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800&q=80', // 커피와 디저트
        'https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800&q=80', // 라떼아트
        'https://images.unsplash.com/photo-1511920170033-f8396924c348?w=800&q=80', // 카페 분위기
        'https://images.unsplash.com/photo-1445116572660-236099ec97a0?w=800&q=80', // 커피 머신
    ],
    restaurant: [
        'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80', // 레스토랑 인테리어
        'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&q=80', // 바베큐/음식
        'https://images.unsplash.com/photo-1550966871-3ed3c47e2ce2?w=800&q=80', // 다이닝
        'https://images.unsplash.com/photo-1590846406792-0adc7f938f1d?w=800&q=80', // 고급 식당
    ],
    park: [
        'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800&q=80', // 푸른 평원/공원
        'https://images.unsplash.com/photo-1519331379826-30da50563d8e?w=800&q=80', // 숲길 산책
        'https://images.unsplash.com/photo-1585938389612-a552a28d6914?w=800&q=80', // 호수 공원
    ],
    culture: [
        'https://images.unsplash.com/photo-1566127444979-b3d2b654e3d7?w=800&q=80', // 전시관
        'https://images.unsplash.com/photo-1518998053901-5348d3969105?w=800&q=80', // 공연장
        'https://images.unsplash.com/photo-1533552026771-479624513689?w=800&q=80', // 현대 미술
    ],
    shopping: [
        'https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=800&q=80', // 쇼핑몰
        'https://images.unsplash.com/photo-1472851294608-415105379664?w=800&q=80', // 플리마켓/거리
    ],
    default: [
        'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800&q=80', // 여행 풍경
        'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&q=80', // 로드트립
        'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=800&q=80', // 호수/산
    ]
};

// 키워드 매핑 테이블
const KEYWORD_MAP: Record<string, string[]> = {
    cafe: ['카페', '커피', '디저트', 'cafe'],
    restaurant: ['식당', '맛집', '요리', '레스토랑', 'restaurant', '밥집'],
    park: ['공원', '산책', '자연', '숲', 'park', '장미원'],
    culture: ['문화', '예술', '전시', '박물관', '미술관', 'acc', 'culture'],
    shopping: ['쇼핑', '백화점', '시장', 'shopping', '몰']
};

/**
 * 장소 태그나 이름을 기반으로 적절한 이미지를 랜덤하게 반환합니다.
 * @param tags 장소 키워드 배열
 * @param name 장소 이름 (보조 키워드 추출용)
 */
export const getCourseImage = (tags: string[] = [], name: string = ''): string => {
    const combinedText = [...tags, name].join(' ').toLowerCase();

    // 1. 카테고리 매칭 확인
    let matchedCategory = 'default';

    for (const [category, keywords] of Object.entries(KEYWORD_MAP)) {
        if (keywords.some(k => combinedText.includes(k))) {
            matchedCategory = category;
            break;
        }
    }

    // 2. 해당 카테고리에서 랜덤 이미지 선택
    const images = PLACE_IMAGES[matchedCategory] || PLACE_IMAGES['default'];
    const randomIndex = Math.floor(Math.random() * images.length);

    return images[randomIndex];
};
