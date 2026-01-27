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
    guests 컬렉션에 저장된 데이터를 users 컬렉션으로 마이그레이션합니다.
    """
    # 1. 설문 및 프로필 데이터 이관
    guest_data = await db["guests"].find_one({"id": guest_id})
    if guest_data:
        # 로그인 유저 정보에 게스트 정보 병합
        await db["users"].update_one(
            {"id": user_id},
            {"$set": {
                "profile": guest_data.get("profile"),
                "survey_data": guest_data.get("survey_data")
            }}
        )
        # 2. 여행 아카이브 데이터 마이그레이션 (owner_id 업데이트)
        await db["user_archive"].update_many(
            {"owner_id": guest_id},
            {"$set": {"owner_id": user_id}}
        )
        # 3. 이관 완료 후 게스트 데이터 삭제
        await db["guests"].delete_one({"id": guest_id})
        print(f"✅ [Migration] Data moved from Guest({guest_id}) to User({user_id})")
        return True
    return False

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
            is_guest=False,
            is_onboarded=bool(user.get("profile")),
            age=user.get("profile", {}).get("age") if user.get("profile") else None,
            gender=user.get("profile", {}).get("gender") if user.get("profile") else None
        )


        return TokenResponse(access_token=access_token, user=user_account)

    except ValueError:
        # Invalid token
        raise HTTPException(status_code=400, detail="Invalid Google token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
