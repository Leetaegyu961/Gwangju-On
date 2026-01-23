# Gwangju-On (광주온) - AI 여행 코스 플래너

광주광역시를 위한 AI 기반 맞춤형 여행 코스 플래너 웹 애플리케이션입니다.
Google Gemini AI를 활용하여 사용자 성향에 맞는 특별한 여행 일정을 설계해 줍니다.

## 🛠 기술 스택 (Tech Stack)

- **프레임워크**: [Next.js 15](https://nextjs.org/) (App Router)
- **언어**: [TypeScript](https://www.typescriptlang.org/)
- **스타일링**: [Tailwind CSS](https://tailwindcss.com/)
- **AI 통합**: Google Generative AI (Gemini)
- **아이콘**: Lucide React

## 🚀 시작하기 (Getting Started)

### 사전 요구사항

- Node.js (최신 LTS 버전 권장)
- npm 또는 yarn

### 설치 방법

1. 저장소 클론:
   ```bash
   git clone <repository-url>
   ```

2. 의존성 설치:
   ```bash
   npm install
   # 또는
   yarn install
   ```

3. 환경 변수 설정:
   루트 경로에 `.env.local` 파일을 생성하고 필요한 키(예: Google AI API Key)를 추가하세요.

### 로컬 실행

개발 서버는 기본적으로 **5000** 포트에서 실행됩니다.

```bash
npm run dev
# 또는
yarn dev
```

브라우저에서 [http://localhost:5000](http://localhost:5000)을 열어 확인하세요.

## 📂 프로젝트 구조

```
frontend/
├── app/                 # Next.js App Router 페이지
│   ├── chat/            # AI 채팅 인터페이스
│   ├── home/            # 메인 랜딩 페이지
│   ├── map/             # 지도 시각화
│   ├── survey/          # 사용자 성향 설문조사
│   └── ...
├── components/          # 재사용 가능한 UI 컴포넌트
│   ├── DiscoverySideModal.tsx
│   └── Navigation.tsx
├── screens/             # 기능별 스크린 컴포넌트
│   ├── HomeScreen.tsx
│   ├── ChatScreen.tsx
│   ├── MapView.tsx
│   └── ...
├── services/            # API 통신 서비스
├── types.ts             # TypeScript 데이터 모델 (User, Course, Place 등)
└── public/              # 정적 에셋
```

## ✨ 주요 기능

- **AI 코스 설계**: 사용자 설문을 바탕으로 개인화된 여행 코스 생성 (`SurveyScreen`)
- **인터랙티브 지도**: 추천 장소 및 경로 시각화 (`MapView`)
- **AI 어시스턴트**: 여행 계획을 구체화하기 위한 AI와의 대화 (`ChatScreen`)
- **마이 페이지**: 저장된 코스 및 프로필 관리 (`MyPage`)
- **반응형 디자인**: 모바일 중심의 프리미엄 UI 디자인

## 📜 스크립트

- `npm run dev`: 개발 서버 실행 (포트 5000)
- `npm run build`: 프로덕션 빌드
- `npm run start`: 프로덕션 서버 실행
- `npm run lint`: ESLint 코드 품질 검사

## 🎨 디자인 시스템

- **주요 색상**: Trust Blue (`#0066FF`)
- **폰트**: Inter (Google Fonts)
- **스타일링**: Glassmorphism 및 부드러운 애니메이션이 적용된 커스텀 Tailwind 설정

---
Developed by **Gwangju-On Team**
