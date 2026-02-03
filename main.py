import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import chat
from backend.db import db as mongo_db, get_database

async def expire_sessions_task():
    """30분 미활동 세션 자동 만료 (EXPIRED) 로직"""
    while True:
        try:
            db = await get_database()
            if db is not None:
                expiry_time = (datetime.now() - timedelta(minutes=30)).isoformat()
                # last_activity_at이 30분 전이면서 상태가 IN_PROGRESS인 세션 조회
                result = await db["user_trip_sessions"].update_many(
                    {
                        "status": "IN_PROGRESS",
                        "last_activity_at": {"$lt": expiry_time}
                    },
                    {"$set": {"status": "EXPIRED"}}
                )
                if result.modified_count > 0:
                    print(f"⏰ [Session Expiry] {result.modified_count} sessions expired.")
        except Exception as e:
            print(f"❌ [Expiry Task Error] {e}")
        
        await asyncio.sleep(60) # 1분마다 체크

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await mongo_db.connect_to_storage()
    # 배경 태스크 시작
    asyncio.create_task(expire_sessions_task())
    yield
    # Shutdown
    await mongo_db.close_storage()

app = FastAPI(title="Gwangju-On Backend", lifespan=lifespan)

# CORS Configuration
origins = [
    "http://localhost:5000", # Frontend dev server
    "http://localhost:3000", # Default Next.js port (fail-safe)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(chat.router, prefix="/api")
from backend.api import user, photo, place_info, tmap, auth, journey, tasting_note, maps
app.include_router(user.router, prefix="/api")
app.include_router(photo.router, prefix="/api")
app.include_router(place_info.router, prefix="/api")  # Mini Agent API
app.include_router(tmap.router, prefix="/api")  # Tmap POI Search
app.include_router(maps.router, prefix="/api")  # Google Static Maps
app.include_router(auth.router, prefix="/api")
app.include_router(journey.router, prefix="/api")
app.include_router(tasting_note.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Gwangju-On Backend is running!"}

