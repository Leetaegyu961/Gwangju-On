from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import chat
from backend.db import db as mongo_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await mongo_db.connect_to_storage()
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
from backend.api import user, photo, place_info, tmap, auth
app.include_router(user.router, prefix="/api")
app.include_router(photo.router, prefix="/api")
app.include_router(place_info.router, prefix="/api")  # Mini Agent API
app.include_router(tmap.router, prefix="/api")  # Tmap POI Search
app.include_router(auth.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Gwangju-On Backend is running!"}

