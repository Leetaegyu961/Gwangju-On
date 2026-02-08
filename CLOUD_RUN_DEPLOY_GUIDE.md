# GCP Cloud Run 배포 가이드

## 아키텍처 구성

```
[사용자 브라우저]
       │
       ▼
[Cloud Run: Frontend]  ──→  [Cloud Run: Backend]  ──→  [Compute Engine VM: MongoDB]
Next.js 15 (port 8080)      FastAPI (port 8080)        mongo:7 (port 27017)
asia-northeast3 (서울)      asia-northeast3 (서울)     asia-northeast3-a (서울)
```

## 서비스 URL

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | https://gwangju-on-frontend-415945034814.asia-northeast3.run.app |
| 백엔드 | https://gwangju-on-backend-415945034814.asia-northeast3.run.app |
| MongoDB VM | 34.22.74.157:27017 (내부용, 외부 직접 접속 비권장) |

## 주요 파일 구조

```
프로젝트 루트/
├── Dockerfile                    # 백엔드 Docker 이미지 (Python 3.13 + Poetry)
├── .dockerignore                 # 백엔드 빌드 제외 목록
├── .gcloudignore                 # Cloud Build 업로드 제외 목록 (vectors.json 포함 허용)
├── cloudbuild-backend.yaml       # 백엔드 CI/CD 설정
├── cloudbuild-frontend.yaml      # 프론트엔드 CI/CD 설정
├── frontend/
│   ├── Dockerfile                # 프론트엔드 Docker 이미지 (Node 20, 멀티스테이지)
│   ├── .dockerignore             # 프론트엔드 빌드 제외 목록
│   └── .env.production           # Cloud Run용 환경변수 (빌드 시 JS에 포함)
└── backend/
    └── main.py                   # CORS에 FRONTEND_URL 환경변수 지원 추가됨
```

---

## 배포 명령어

### 사전 준비
```powershell
gcloud auth login
gcloud config set project jnu-rise-edu-134
```

### 백엔드 배포 (프로젝트 루트에서 실행)
```powershell
gcloud run deploy gwangju-on-backend `
    --source . `
    --region asia-northeast3 `
    --allow-unauthenticated `
    --port 8080 `
    --memory 2Gi --cpu 1 `
    --min-instances 1 `
    --max-instances 10 `
    --quiet
```

### 프론트엔드 배포 (프로젝트 루트에서 실행)
```powershell
gcloud run deploy gwangju-on-frontend `
    --source frontend `
    --region asia-northeast3 `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi `
    --min-instances 1 `
    --quiet
```

> 프론트엔드 환경변수는 `frontend/.env.production`에서 빌드 시 자동 로드됨.
> 백엔드 환경변수는 Cloud Run 서비스 설정에 저장되어 있음 (재배포해도 유지).

---

## 환경변수 관리

### 백엔드 환경변수 확인
```powershell
gcloud run services describe gwangju-on-backend --region asia-northeast3 --format="yaml(spec.template.spec.containers[0].env)"
```

### 백엔드 환경변수 수정
```powershell
gcloud run services update gwangju-on-backend `
    --region asia-northeast3 `
    --update-env-vars "키=값" `
    --quiet
```

### 현재 설정된 백엔드 환경변수 목록
- `GOOGLE_API_KEY` - Google AI Studio API 키
- `GOOGLE_CLOUD_API_KEY` - GCP API 키 (Places Photo 프록시용)
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` - 네이버 블로그 검색
- `TMAP_APP_KEY` - TMAP POI 검색
- `GOOGLE_CLIENT_ID` - Google OAuth 클라이언트 ID
- `MONGO_URI` - MongoDB 연결 문자열
- `FRONTEND_URL` - 프론트엔드 URL (CORS 허용)
- `API_URL` - 백엔드 자체 URL (사진 프록시 URL 생성용)

### 프론트엔드 환경변수 (`frontend/.env.production`)
- `NEXT_PUBLIC_API_URL` - 백엔드 API URL (/api 포함)
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` - Google OAuth 클라이언트 ID
- `NEXT_PUBLIC_TMAP_APP_KEY` - TMAP API 키

> `NEXT_PUBLIC_*` 변수는 빌드 시점에 JS 번들에 포함됨. 변경 시 프론트엔드 재배포 필요.

---

## 로그 확인

### CMD에서 실시간 로그 (beta 설치 필요)
```powershell
# beta 설치 (관리자 CMD에서 1회만)
gcloud components install beta

# 백엔드 실시간 로그
gcloud beta run services logs tail gwangju-on-backend --region asia-northeast3

# 프론트엔드 실시간 로그
gcloud beta run services logs tail gwangju-on-frontend --region asia-northeast3
```

### beta 없이 로그 확인
```powershell
# 최근 30건 로그
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gwangju-on-backend" --limit=30 --format="table(timestamp,textPayload)" --freshness=10m
```

### 웹 콘솔에서 실시간 로그 (가장 편함)
- 백엔드: https://console.cloud.google.com/run/detail/asia-northeast3/gwangju-on-backend/logs?project=jnu-rise-edu-134
- 프론트엔드: https://console.cloud.google.com/run/detail/asia-northeast3/gwangju-on-frontend/logs?project=jnu-rise-edu-134

---

## Cold Start 관리

```powershell
# 항상 1개 인스턴스 유지 (빠른 응답, 시연용)
gcloud run services update gwangju-on-backend --region asia-northeast3 --min-instances 1 --quiet
gcloud run services update gwangju-on-frontend --region asia-northeast3 --min-instances 1 --quiet

# 유휴 시 자동 종료 (비용 절약)
gcloud run services update gwangju-on-backend --region asia-northeast3 --min-instances 0 --quiet
gcloud run services update gwangju-on-frontend --region asia-northeast3 --min-instances 0 --quiet
```

---

## MongoDB VM 관리

```powershell
# VM 상태 확인
gcloud compute instances describe mongodb-server --zone=asia-northeast3-a --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"

# VM 중지 (디스크 비용만 발생 ~$0.3/월)
gcloud compute instances stop mongodb-server --zone=asia-northeast3-a

# VM 시작
gcloud compute instances start mongodb-server --zone=asia-northeast3-a

# SSH 접속
gcloud compute ssh mongodb-server --zone=asia-northeast3-a

# MongoDB 컨테이너 상태 확인 (SSH 접속 후)
sudo docker ps
sudo docker logs mongodb
```

### MongoDB 접속 정보
- Host: `34.22.74.157`
- Port: `27017`
- User: `admin`
- Password: `gwangju2025!`
- URI: `mongodb://admin:gwangju2025!@34.22.74.157:27017/gwangju_on?authSource=admin`

---

## 서비스 중단/삭제

```powershell
# Cloud Run 서비스 삭제
gcloud run services delete gwangju-on-frontend --region asia-northeast3
gcloud run services delete gwangju-on-backend --region asia-northeast3

# MongoDB VM 삭제
gcloud compute instances delete mongodb-server --zone=asia-northeast3-a

# 방화벽 규칙 삭제
gcloud compute firewall-rules delete allow-mongodb
```

---

## 월간 예상 비용

| 항목 | min-instances 0 | min-instances 1 |
|------|----------------|----------------|
| Cloud Run 백엔드 | ~$0 (유휴 시) | ~$3~5/월 |
| Cloud Run 프론트엔드 | ~$0 (유휴 시) | ~$2~3/월 |
| MongoDB VM (e2-small) | ~$8/월 (켜놓을 때) | ~$8/월 |
| VM 디스크 10GB | ~$0.4/월 | ~$0.4/월 |
| **합계** | **~$8.4/월** | **~$14/월** |

> VM을 stop 해두면 디스크 비용 $0.4/월만 발생.

---

## CI/CD 설정 (GitHub → 자동 배포)

1. GCP Console → Cloud Build → Triggers → "Connect Repository"로 GitHub 연결
2. 백엔드 트리거 생성:
   - Event: Push to branch `main`
   - Included files: `backend/**`, `src/**`, `pyproject.toml`, `Dockerfile`
   - Build config: `cloudbuild-backend.yaml`
3. 프론트엔드 트리거 생성:
   - Event: Push to branch `main`
   - Included files: `frontend/**`
   - Build config: `cloudbuild-frontend.yaml`

---

## 트러블슈팅

### 빌드 실패 시 로그 확인
```powershell
gcloud builds list --region=asia-northeast3 --limit=1 --format="value(id)"
gcloud builds log [BUILD_ID] --region=asia-northeast3
```

### 자주 발생하는 문제
| 문제 | 원인 | 해결 |
|------|------|------|
| `vectors.json not found` | `.gitignore`에 포함, `.gcloudignore` 미설정 | `.gcloudignore`에서 제외하지 않음 |
| `npm ERESOLVE` | framer-motion + React 19 충돌 | `npm install --legacy-peer-deps` |
| `useSearchParams Suspense` | Next.js 15 SSG 요구사항 | 페이지를 `<Suspense>`로 감싸기 |
| 사진 안 보임 | 백엔드 `API_URL` 환경변수 미설정 | `API_URL=https://백엔드URL` 추가 |
| CORS 에러 | `FRONTEND_URL` 미설정 | 백엔드에 프론트 URL 환경변수 추가 |
| `NEXT_PUBLIC_*` 적용 안 됨 | 런타임이 아닌 빌드 시점에 필요 | `frontend/.env.production` 사용 |

### Google OAuth 설정
GCP Console → APIs & Services → Credentials에서 OAuth Client ID의 Authorized JavaScript Origins에 프론트엔드 Cloud Run URL 추가 필요.
