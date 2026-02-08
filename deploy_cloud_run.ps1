$PROJECT_ID = gcloud config get-value project
$REGION = "asia-northeast3" # Seoul Region

if (-not $PROJECT_ID) {
    Write-Host "Error: No Google Cloud Project selected. Run 'gcloud config set project [PROJECT_ID]' first." -ForegroundColor Red
    exit 1
}

Write-Host "🚀 Starting Deployment to Google Cloud Run (Project: $PROJECT_ID, Region: $REGION)..." -ForegroundColor Cyan

# 1. Backend + Agent Deployment
Write-Host "`n📦 Deploying Backend + Agent..." -ForegroundColor Yellow
gcloud run deploy gwangju-on-backend `
    --source . `
    --dockerfile Dockerfile.backend `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --memory 2Gi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend Deployment Failed!" -ForegroundColor Red
    exit 1
}

# 2. Frontend Deployment
Write-Host "`n🖥️ Deploying Frontend (Next.js)..." -ForegroundColor Yellow
Push-Location frontend
gcloud run deploy gwangju-on-frontend `
    --source . `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend Deployment Failed!" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host "`n✅ All Services Deployed Successfully!" -ForegroundColor Green
Write-Host "Please update the Frontend's API URL to point to the new Backend URL if needed." -ForegroundColor Gray
