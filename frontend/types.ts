
/**
 * [Data Models]
 * 애플리케이션 전체에서 사용되는 일관된 데이터 구조 정의
 */

// 사용자 프로필 정보
export interface UserProfile {
  id: string;
  nickname: string;
  age: number;
  gender: '남성' | '여성' | '';
  isLoggedIn: boolean;
  preferences: string[];
}

// 근거 카드 정보 (추천 이유, 리뷰 요약, 리스크 등)
export interface EvidenceCard {
  placeId: string;
  name?: string;       // 장소 이름 (추가)
  reason: string;      // "이런 분들께 추천해요"
  reviewSummary: string; // 핵심 리뷰 요약
  risks?: string;      // 주의사항 (사람이 많아요 등)
  trustScore: number;  // 신뢰도 점수 (0-100)
  lat?: number;        // 위도
  lng?: number;        // 경도
  keywords?: string[]; // 태그/키워드
  img?: string;        // 실제 이미지 URL (Google Photo)
}

// 여행 코스를 구성하는 각 개별 지점 정보
export interface CoursePoint {
  id: string;
  type: '식당' | '카페' | '놀거리' | '공연' | '숙박' | '선택 전';
  name: string;
  address?: string;
  lat?: number;
  lng?: number;
  imageUrl?: string;
  reason?: string;
  evidence?: EvidenceCard;
  // Extra fields for map/history compatibility
  desc?: string;
  tags?: string[];
  transport?: string;
  img?: string;
}

// 저장된 최종 여행 코스 데이터
export interface SavedCourse {
  id: string;
  userId: string;
  title: string;
  points: CoursePoint[];
  totalBudget: string;
  createdAt: string;
  description: string;
}

// AI가 추천하는 코스 구조 (Backend: RecommendedCourse)
export interface RecommendedCourse {
  course_id: number;
  course_name: string;
  course_description: string;
  places: EvidenceCard[];
  total_budget: string;
}

// AI와 주고받는 메시지 객체
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  isDecisionPoint?: boolean;
  evidenceCards?: EvidenceCard[]; // AI 응답 하단에 노출될 근거 카드 목록 (Legacy or Single)
  courses?: RecommendedCourse[];  // [New] 다중 코스 추천 리스트
  status?: 'analyzing' | 'searching' | 'generating' | 'done'; // 진행 단계
  suggestions?: string[]; // 사용자에게 제안할 답변 선택지
}

// 지도나 리스트에서 활용할 장소 마스터 데이터
export interface Place {
  id: string;
  name: string;
  category: string;
  description: string;
  imageUrl: string;
  tags: string[];
  reviewSnippets: string[];
  lat: number;
  lng: number;
}