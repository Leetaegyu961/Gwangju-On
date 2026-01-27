from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserProfile(BaseModel):
    gender: str
    age: str

class UserAccount(BaseModel):
    id: str  # Google sub or user_id
    email: Optional[EmailStr] = None # Guest might not have email
    name: str
    picture: Optional[str] = None
    is_guest: bool = False
    is_onboarded: bool = False
    age: Optional[str] = None
    gender: Optional[str] = None
    saved_course_ids: List[str] = []
    travel_log_ids: List[str] = []


class CoursePoint(BaseModel):
    id: str
    type: str
    name: str

class SurveyResult(BaseModel):
    userId: str
    courses: List[CoursePoint]
    themes: List[str]
    companions: List[str]
    budget: List[int]

class OnboardingResponse(BaseModel):
    userId: str
    message: str

class GoogleLoginRequest(BaseModel):
    id_token: str
    guest_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserAccount

