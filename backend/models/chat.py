from pydantic import BaseModel
from typing import List, Optional

class EvidenceCard(BaseModel):
    placeId: str
    name: Optional[str] = None
    reason: str
    reviewSummary: str
    risks: Optional[str] = None
    trustScore: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    keywords: Optional[List[str]] = None
    img: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    userId: Optional[str] = None # Frontend에서 userId를 보내줄 수 있도록 추가

class RecommendedCourse(BaseModel):
    course_id: int
    course_name: str
    course_description: str
    places: List[EvidenceCard]
    total_budget: str

class ChatResponse(BaseModel):
    id: str
    role: str
    text: str
    isDecisionPoint: Optional[bool] = False
    evidenceCards: Optional[List[EvidenceCard]] = None
    courses: Optional[List[RecommendedCourse]] = None
    status: Optional[str] = "done"
