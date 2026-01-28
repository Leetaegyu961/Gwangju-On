from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.db import db
from backend.api import chat, user, photo, tmap, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 DB 연결
    await db.connect_to_storage()
    yield
    # 앱 종료 시 DB 연결 해제
    await db.close_storage()

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
app.include_router(user.router, prefix="/api")
app.include_router(photo.router, prefix="/api")
app.include_router(tmap.router, prefix="/api")
app.include_router(auth.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Gwangju-On Backend is running!"}
