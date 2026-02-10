from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from google.cloud import storage
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "gwangju-on-photos")
GCS_KEY_PATH = os.getenv("GCS_KEY_PATH", "")


def get_gcs_client():
    """로컬: 키 파일 사용 / Cloud Run: 서비스 계정 자동 인증"""
    if GCS_KEY_PATH and os.path.exists(GCS_KEY_PATH):
        return storage.Client.from_service_account_json(GCS_KEY_PATH)
    return storage.Client()


@router.post("/upload/photo")
async def upload_photo(
    file: UploadFile = File(...),
    user_id: str = Query("anonymous"),
    session_id: str = Query("unknown"),
    spot_index: int = Query(0),
):
    # 이미지 파일 검증
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Image files only")

    contents = await file.read()

    # 10MB 제한
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # 고유 파일명 생성
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    blob_name = f"photos/{user_id}/{session_id}/{spot_index}_{uuid.uuid4().hex[:8]}.{ext}"

    try:
        client = get_gcs_client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_name)

        blob.upload_from_string(contents, content_type=file.content_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

        return {
            "status": "success",
            "url": public_url,
            "blob_name": blob_name,
        }
    except Exception as e:
        print(f"GCS Upload Error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
