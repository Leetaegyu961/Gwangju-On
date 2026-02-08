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
    게스트 세션(user_trip_sessions) 및 아카이브 기록을 실제 유저 계정으로 이관합니다.
    """
    # 1. Trip Sessions 이관 (userId 업데이트 및 created_at 확인)
    trip_session = await db["user_trip_sessions"].find_one({"userId": guest_id})
    if trip_session:
        # 기존 세션의 userId를 신규 유저 ID로 변경
        await db["user_trip_sessions"].update_one(
            {"userId": guest_id},
            {"$set": {
                "userId": user_id,
                "migrated_at": datetime.utcnow() # 마이그레이션 시점 기록
            }}
        )
        # 만약 기존 users 컬렉션에 profile이 없으면 demographics 정보를 복사함
        await db["users"].update_one(
            {"id": user_id},
            {"$set": {
                "profile": trip_session.get("demographics"),
                "survey_data": trip_session.get("survey_data")
            }}
        )
        print(f"📦 [Migration] Trip Session for {guest_id} moved to {user_id}")

    # 2. 여행 아카이브 데이터 마이그레이션 (owner_id 또는 userId 업데이트)
    # user_archive는 'userId' 필드를 사용함 (user.py 참고)
    archive_result = await db["user_archive"].update_many(
        {"userId": guest_id},
        {"$set": {"userId": user_id}}
    )
    if archive_result.modified_count > 0:
        print(f"📜 [Migration] {archive_result.modified_count} archive items moved to {user_id}")

    # 3. 구형 guests 컬렉션 데이터가 남아있다면 이관 (하위 호환성)
    guest_data = await db["guests"].find_one({"id": guest_id})
    if guest_data:
        await db["users"].update_one(
            {"id": user_id},
            {"$set": {
                "profile": guest_data.get("profile"),
                "survey_data": guest_data.get("survey_data")
            }}
        )
        await db["guests"].delete_one({"id": guest_id})
        print(f"✅ [Migration] Legacy Guest data moved for {user_id}")
    
    return True

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
            # 프로필 정보 업데이트 (이메일은 같지만 ID가 다를 경우 ID도 동기화)
            update_data = {"name": user_name, "picture": user_picture, "last_login": datetime.utcnow()}
            if user.get("id") != google_id:
                update_data["id"] = google_id
                print(f"🔄 [Auth] Updating User ID from {user.get('id')} to {google_id}")
            
            await users_col.update_one(
                {"email": user_email},
                {"$set": update_data}
            )

        # 3. 데이터 마이그레이션 (guest_id가 제공된 경우)
        if request.guest_id:
            migration_success = await migrate_user_data(db, request.guest_id, google_id)
            if migration_success:
                # 마이그레이션 후 최신 유저 정보 다시 조회
                user = await users_col.find_one({"email": user_email})

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

# --- [New] Token Verification & /auth/me ---
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    db = await get_database()
    user = await db["users"].find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if "_id" in user: user.pop("_id")
    return user

@router.get("/auth/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    현재 로그인된 사용자 정보 반환 (ID 대신 토큰 사용)
    """
    return current_user
