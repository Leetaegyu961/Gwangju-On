from pydantic import BaseModel
from datetime import datetime

class Demographics(BaseModel):
    age: str | None = None
    gender: str | None = None

class CoursePoint(BaseModel):
    id: str
    type: str
    name: str
    lat: float | None = None
    lng: float | None = None
    desc: str | None = None
    tags: list[str] = []
    transport: str | None = None
    img: str | None = None

class SurveyData(BaseModel):
    region: str | None = None
    courses: list[CoursePoint] = []
    themes: list[str] = []
    companions: list[str] = []
    budget: list[int] = []

class UserTripSession(BaseModel):
    userId: str
    created_at: str | None = None
    demographics: Demographics
    survey_data: SurveyData
    chat_context: list[dict] = []
    status: str = "pending" # pending or completed

class UserProfile(BaseModel):
    gender: str
    age: str

class SurveyResult(BaseModel):
    userId: str
    region: str | None = None
    courses: list[CoursePoint]
    themes: list[str]
    companions: list[str]
    budget: list[int]
    chat_log: list[dict] = []
    has_specific_place: str = "N" # Y or N

class OnboardingResponse(BaseModel):
    userId: str
    message: str

class GoogleLoginRequest(BaseModel):
    id_token: str
    guest_id: str | None = None

class UserAccount(BaseModel):
    id: str
    email: str
    name: str
    picture: str
    is_guest: bool
    is_onboarded: bool = False
    age: str | None = None
    gender: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    user: UserAccount

class UserArchive(BaseModel):
    id: str
    userId: str
    title: str
    points: list[CoursePoint]
    totalBudget: str
    createdAt: str
    description: str | None = None
