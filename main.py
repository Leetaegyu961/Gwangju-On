from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import chat

app = FastAPI(title="Gwangju-On Backend")

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
from backend.api import user, photo
app.include_router(user.router, prefix="/api")
app.include_router(photo.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Gwangju-On Backend is running!"}
