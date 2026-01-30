from pydantic import BaseModel
from typing import List, Optional, Any

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

class CourseInfo(BaseModel):
    course_id: int
    course_name: str
    course_description: Optional[str] = ""
    cards: List[EvidenceCard]

class ChatRequest(BaseModel):
    message: str
    userId: Optional[str] = None # Frontend에서 userId를 보내줄 수 있도록 추가

class ChatResponse(BaseModel):
    id: str
    role: str
    text: str
    isDecisionPoint: Optional[bool] = False
    evidenceCards: Optional[List[EvidenceCard]] = None
    allCourses: Optional[List[CourseInfo]] = None  # 3개 코스 전체
    status: Optional[str] = "done"
