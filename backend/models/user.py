from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

class Demographics(BaseModel):
    age: Optional[str] = None
    gender: Optional[str] = None

class CoursePoint(BaseModel):
    id: str
    type: str
    name: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    desc: Optional[str] = None
    tags: List[str] = []
    transport: Optional[str] = None
    img: Optional[str] = None

class SurveyData(BaseModel):
    region: Optional[str] = None
    courses: List[CoursePoint] = []
    themes: List[str] = []
    companions: List[str] = []
    budget: List[int] = []
    has_specific_place: str = "N"

class IntentContext(BaseModel):
    survey_data: SurveyData
    chat_history: List[Dict[str, Any]] = []
    keywords: List[str] = []

class UserTripSession(BaseModel):
    sessionId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    status: str = "IN_PROGRESS" # IN_PROGRESS, COMPLETED, RESTARTED, EXPIRED, ABANDONED
    intent_context: IntentContext
    album_data: List[Dict[str, Any]] = []
    last_activity_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Legacy fields for fallback
    demographics: Optional[Demographics] = None
    survey_data: Optional[SurveyData] = None
    chat_context: List[Dict[str, Any]] = []

class UserActivityLog(BaseModel):
    logId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sessionId: str
    action_type: str # PICK, SKIP, REJECT
    target_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class TastingNoteEntry(BaseModel):
    noteId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sessionId: str
    satisfaction: int
    atmosphere: str
    movement: str
    best_place_id: str
    ai_quality: str
    raw_response: Dict[str, Any]
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

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
