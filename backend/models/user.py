from pydantic import BaseModel

class UserProfile(BaseModel):
    gender: str
    age: str

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

class SurveyResult(BaseModel):
    userId: str
    courses: list[CoursePoint]
    themes: list[str]
    companions: list[str]
    budget: list[int]

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