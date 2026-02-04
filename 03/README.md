# v4.5 작업 통합 요약 및 소스코드 (03 Export)

이 데이터는 `proV4`에서 진행된 **Wishlist(찜한 코스)** 및 **Invitation(여행 초대장)** 시스템의 최신 소스코드를 포함하고 있습니다. (발표 편의를 위해 24시간 노출 억제 기능은 코드 레벨에서 완전히 제외되었습니다.)

## 1. 주요 변경 사항 (Wishlist & Invitation 최신화)

### ✉️ 여행 초대장 (SummarySequence.tsx / InvitationPopup.tsx)
- **AI 컨텍스트 트리거**: 사용자의 행동(설문 진입, 지도 탐색 등)을 실시간으로 파악하여 가장 적절한 '여행 카드'를 제안합니다.
- **인터랙티브 팝업 디자인**: 고화질 이미지와 매력적인 카피를 포함한 전용 모달(InvitationPopup)로 사용자 경험을 강화했습니다.
- **세션 기반 최적화**: 동일 세션 내 중복 노출을 제어하여 사용자의 흐름을 방해하지 않도록 설계되었습니다.
- **게스트 참여 유도 (Guest-Inclusive)**: 비회원에게도 핵심 여정을 제안하여 자연스러운 서비스 체험과 가입을 유도합니다.
- **활동 데이터 사일런트 로깅**: 초대장 수락/거절 이력을 무음 처리하여 향후 AI 추천 고도화를 위한 데이터로 활용합니다.
- **데이터 구조 최적화**: 타임라인과 Wishlist 간 이미지(`imageUrl`) 및 설명(`description`) 데이터 매핑 로직을 강화했습니다.

### 💖 찜한 코스 (WishlistScreen.tsx)
- **리스트 뷰(List View) 도입**: 여러 개의 찜한 코스를 관리할 수 있는 목록 화면을 추가했습니다.
- **상세 뷰 연동**: 목록에서 항목 클릭 시 상세 내용을 확인하고, 다시 목록으로 돌아오는 순환 구조를 구축했습니다.
- **명칭 통일**: '여행 계획'을 '코스'로 통일하여 사용자 인지적 일관성을 높였습니다.

---

## 2. 포함된 소스코드 목록
- `frontend/screens/WishlistScreen_v4_5.tsx`: 목록/상세 전환 기능이 포함된 찜 화면
- `frontend/features/experience/SummarySequence_v4_5.tsx`: 데이터 매핑 및 세션 연동이 강화된 초대장 화면
- `frontend/screens/TimelineScreen_v4_5.tsx`: '11' 레퍼런스 스타일이 적용된 타임라인/추억 앨범 화면
- `frontend/app/timeline/TimelinePage_v4_5.tsx`: 타임라인 화면의 `Suspense` 래퍼 (빌드 오류 수정용)
- `frontend/screens/MyPage_v4_5.tsx`: '찜한 코스' 명칭 및 데이터 연동이 업데이트된 마이페이지
- `backend/data/`: 여행 코스 및 장소 데이터 원본 파일들 (4종)
- `README.md`: 현재 이 가이드 문서

---

## 3. 핵심 로직 요약

### 초대장 데이터 매핑 (SummarySequence)
```tsx
// 타임라인/Wishlist와 형식을 맞추기 위한 수동 매핑
const mapPoints = pickedPlaces.map((p, i) => ({
    id: p.id || i.toString(),
    name: p.name,
    lat: p.lat,
    lng: p.lng,
    desc: p.description || p.reason || '',
    img: p.imageUrl // Timeline에서 사용하는 필드명과 일치
}));
```

### 찜 목록 전환 엔진 (WishlistScreen)
```tsx
const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');
// mode에 따른 조건부 렌더링으로 UX 유연성 확보
```

---

## 4. 백엔드 및 기타 사항
- `backend/main_v4_5.py`: 세션 업데이트 및 위시리스트 저장 API가 포함된 백엔드 로직
- `data/invitation_courses.json`: 에이전트 추천 코스의 기반이 되는 정적 데이터셋
