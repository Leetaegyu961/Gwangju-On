
// 여행 장소 카테고리별 고품질 이미지 매핑 유틸리티
// 실제 프로젝트에서는 CDN이나 더 많은 이미지 리스트를 활용할 수 있습니다.

// 키워드별 이미지 URL 리스트 (Unsplash Source)
const PLACE_IMAGES: Record<string, string[]> = {
    cafe: [
        'https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&q=80', // 라떼아트/카페
        'https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=600&q=80', // 힙한 카페
        'https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=600&q=80', // 야외 카페
        'https://images.unsplash.com/photo-1493857671505-72967e2e2760?w=600&q=80', // 아침 커피
    ],
    restaurant: [
        'https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=600&q=80', // 분위기 있는 식당
        'https://images.unsplash.com/photo-1559339352-11d035aa65de?w=600&q=80', // 모던 레스토랑
        'https://images.unsplash.com/photo-1550966871-3ed3c47e2ce2?w=600&q=80', // 디너 테이블
        'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&q=80', // 고급 요리
    ],
    park: [
        'https://images.unsplash.com/photo-1596436889106-be35c843f974?w=600&q=80', // 장미원 느낌
        'https://images.unsplash.com/photo-1498855926480-d98e83099315?w=600&q=80', // 숲길
        'https://images.unsplash.com/photo-1519331379826-30da50563d8e?w=600&q=80', // 햇살 공원
    ],
    culture: [
        'https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=600&q=80', // 박물관/건축물 (ACC 느낌)
        'https://images.unsplash.com/photo-1499364615650-ec387c133db9?w=600&q=80', // 갤러리
        'https://images.unsplash.com/photo-1518998053901-5348d3969105?w=600&q=80', // 공연장
    ],
    shopping: [
        'https://images.unsplash.com/photo-1534452286882-6fc6910939b0?w=600&q=80', // 쇼핑몰
        'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=80', // 편집샵
    ],
    default: [
        'https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=600&q=80', // 여행 가방/지도
        'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=600&q=80', // 어딘가 떠나는 느낌
        'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600&q=80', // 풍경
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
