# 🎨 Gwangju-On UI/UX 리뉴얼 보고서 (v3.3)

## 1. 개요 (Overview)
본 프로젝트는 **"사용자 친화적(User-Friendly)"**이고 **"감성적인(Emotional)"** 사용자 경험을 제공하기 위해 전면적인 UI/UX 리뉴얼을 진행했습니다.
마스코트 캐릭터를 적극적으로 활용하여 앱의 가이드 역할을 부각시켰으며, 모든 화면에서 일관된 **Soft & Warm** 디자인 언어를 적용했습니다.

---

## 2. 주요 변경 사항 및 코드 상세 (Detailed Changelog)

### 🎨 `frontend/app/globals.css`
**"디자인 시스템 재정의 (Variables & Utilities)"**
*   **CSS Variables:** `:root`에 따뜻한 미색 배경(`--background-start-rgb: 253, 251, 247`)과 부드러운 텍스트 컬러 정의.
*   **Utility Classes:**
    *   `.hide-scrollbar`: `::-webkit-scrollbar { display: none; }`를 사용하여 스크롤바 숨김 처리.
    *   `.glass-morphism`: `backdrop-filter: blur(10px)`와 `bg-white/30`을 조합한 유리 질감 효과 클래스 추가.
    *   `.animate-fade-in`: 투명도(`opacity`)와 위치(`transform`)를 조절하는 `@keyframes` 애니메이션 정의.

### 🐭 `frontend/screens/LoginScreen.tsx`
**"생동감 있는 마스코트 영상 배경 적용"**
*   **Video Tag Implementation (L130~):**
    ```tsx
    <video autoPlay loop muted playsInline className="...">
      <source src="/mascot_animation.mp4" type="video/mp4" />
    </video>
    ```
    기존 `<img>` 배경을 `<video>` 태그로 교체하여 루핑 애니메이션 구현.
*   **Overlay Layer:** 영상 위에 `bg-black/30` 오버레이를 씌워 텍스트 가독성 확보.
*   **Button Style:** `rounded-full`, `backdrop-blur-md`, `active:scale-95` 클래스를 적용해 터치감 개선.

### 👤 `frontend/screens/ProfileSetupScreen.tsx`
**"인터랙티브한 Grid 레이아웃 도입"**
*   **Grid Layout Conversion (L98, L125):**
    기존 `flex-col` 구조를 `grid grid-cols-2 gap-4`(성별), `grid grid-cols-3 gap-3`(연령)으로 변경하여 공간 효율성 증대.
*   **Conditional Styling (clsx pattern):**
    ```tsx
    className={`... ${selectedGender === 'male' ? 'border-[#0066FF] bg-blue-50' : 'border-transparent'}`}
    ```
    상태(`state`)에 따라 테두리 색상과 배경색이 즉시 변경되도록 조건부 스타일링 적용.

### 📝 `frontend/screens/SurveyScreen.tsx`
**"따뜻한 톤앤매너와 슬라이더 UI"**
*   **Background Color:** 최상위 컨테이너에 `bg-[#FDFBF7]`(Warm Beige) 적용.
*   **Custom Slider UI:** 예산 설정 부분에 `<input type="range">`를 커스텀 스타일링하여 적용.
*   **Mascot Greeting:** 헤더 영역에 마스코트 이미지와 말풍선 컴포넌트 추가 (`absolute` 포지셔닝 활용).

### 💬 `frontend/screens/ChatScreen.tsx`
**"마스코트 페르소나 주입"**
*   **Avatar Replacement (L184):**
    `Lucide React`의 `<Bot />` 아이콘을 삭제하고, `<img src="/mascot_circle.png" />`로 교체하여 캐릭터성 부여.
*   **Loading Component (L259):**
    단순 로딩 텍스트를 `animate-bounce` 클래스가 적용된 마스코트 이미지와 말풍선 UI(`flex items-center gap-3`)로 전면 교체.

### 📍 `frontend/screens/MapView.tsx`
**"Tmap 커스텀 오버레이 마커 구현"**
*   **Marker Logic (L530~):** `Tmapv3.Marker`의 `iconHTML` 속성에 커스텀 HTML 문자열 주입.
    ```html
    <div style="...">
      <img src="/mascot_circle.png" ... /> <!-- 마스코트 얼굴 -->
      <div style="..."> ${index + 1} </div> <!-- 순서 뱃지 -->
    </div>
    ```
*   **Dynamic Scaling:** `activeStep === index` 조건일 때 `transform: scale(1.2)` 및 `z-index: 10`을 적용하여 현재 단계 강조.

### 📜 `frontend/screens/HistoryScreen.tsx`
**"빈 상태(Empty State)의 시각화"**
*   **Conditions (L64):** `courses.length === 0` 조건문 분기 처리 강화.
*   **Illustration:** 흑백 처리된 마스코트 이미지(`grayscale-[20%] opacity-80`)와 유도 문구 배치.
*   **CTA Button:** `/chat`으로 이동하는 '여행 시작하기' 버튼 추가 (스타일: `shadow-blue-200`, `rounded-full`).

### 👤 `frontend/screens/MyPage.tsx`
**"카드형 UI로 정보 구조화"**
*   **Header SVG Logic:** 프로필 이미지 주변에 장식용 아이콘(`Sparkles`, `TrendingUp`)을 절대 좌표(`absolute`)로 배치.
*   **Menu Restructuring:** 단순 `<ul>` 리스트를 `border border-gray-100`과 `shadow-sm`을 가진 카드 버튼 컴포넌트로 변경.

---

## 3. 디자인 시스템 (Design System)

| 요소 (Element) | 스타일 (Style) | 코드 예시 (Tailwind) |
| :--- | :--- | :--- |
| **Color** | Warm Beige & Trust Blue | `bg-[#FDFBF7]`, `text-[#0066FF]` |
| **Shape** | Super Rounded (Pill/Circle) | `rounded-full`, `rounded-[2rem]` |
| **Shadow** | Soft & Diffused | `shadow-sm`, `shadow-blue-100` |
| **Interaction** | Bounce & Scale | `active:scale-95`, `hover:scale-105`, `animate-bounce` |
| **Typography** | Pretendard / Inter | `font-bold`, `leading-relaxed` |

---

## 4. 리소스 (Assets)
*   **`public/mascot_circle.png`**: 프로필, 지도 마커용 원형 마스코트.
*   **`public/mascot_full.png`**: 설문조사, 빈 화면용 마스코트 전신.
*   **`public/mascot_animation.mp4`**: 로그인 화면용 루핑 영상.
