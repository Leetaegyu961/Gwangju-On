// API URL 중앙 관리
// 로컬: .env → http://localhost:8000/api
// Cloud Run: .env.production → https://gwangju-on-backend-xxx.run.app/api
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// /api를 제외한 Base URL (static 파일, 이미지 경로 등에 사용)
export const API_BASE_URL = API_URL.replace(/\/api\/?$/, '');
