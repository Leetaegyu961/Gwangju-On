import os
from fastapi import APIRouter, HTTPException, Depends, Response
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
from backend.models.user import GoogleLoginRequest, TokenResponse, UserAccount
from backend.db import get_database
import uuid

router = APIRouter()

# Environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET", "default_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def migrate_user_data(db, guest_id: str, user_id: str):
    """
    guest_id에 저장된 모든 데이터를 user_id로 마이그레이션합니다.
    """
    # 여행 아카이브 데이터 마이그레이션
    # 'owner_id' 필드를 guest_id에서 user_id로 업데이트
    archive_collection = db["user_archive"]
    result = await archive_collection.update_many(
        {"owner_id": guest_id},
        {"$set": {"owner_id": user_id}}
    )
    
    # 설문 결과 및 프로필도 마이그레이션
    user_collection = db["users"]
    guest_data = await user_collection.find_one({"id": guest_id})
    if guest_data:
        # 로그인 유저 정보에 게스트 정보 일부 병합 (예: 설문 데이터)
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {
                "survey_data": guest_data.get("survey_data"),
                "profile": guest_data.get("profile")
            }}
        )
        # 병합 후 게스트 레코드 삭제 (선택 사항)
        await user_collection.delete_one({"id": guest_id})

    return result.modified_count

@router.post("/auth/google", response_model=TokenResponse)
async def google_login(request: GoogleLoginRequest, response: Response):
    try:
        # 1. Google ID Token 검증
        idinfo = id_token.verify_oauth2_token(
            request.id_token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        user_email = idinfo['email']
        user_name = idinfo.get('name', '')
        user_picture = idinfo.get('picture', '')
        google_id = idinfo['sub']

        db = await get_database()
        users_col = db["users"]

        # 2. 사용자 조회 또는 생성 (Upsert)
        user = await users_col.find_one({"email": user_email})
        
        if not user:
            user = {
                "id": google_id,
                "email": user_email,
                "name": user_name,
                "picture": user_picture,
                "is_guest": False,
                "created_at": datetime.utcnow()
            }
            await users_col.insert_one(user)
        else:
            # 프로필 정보 업데이트
            await users_col.update_one(
                {"email": user_email},
                {"$set": {"name": user_name, "picture": user_picture, "last_login": datetime.utcnow()}}
            )

        # 3. 데이터 마이그레이션 (guest_id가 제공된 경우)
        if request.guest_id:
            await migrate_user_data(db, request.guest_id, google_id)

        # 4. JWT 생성
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": google_id, "email": user_email}, 
            expires_delta=access_token_expires
        )

        user_account = UserAccount(
            id=google_id,
            email=user_email,
            name=user_name,
            picture=user_picture,
            is_guest=False
        )

        return TokenResponse(access_token=access_token, user=user_account)

    except ValueError:
        # Invalid token
        raise HTTPException(status_code=400, detail="Invalid Google token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
