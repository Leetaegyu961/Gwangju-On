from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class PlaceMetadata(BaseModel):
    id: str = Field(..., description="Google Place ID or unique ID")
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    lat: float
    lng: float
    stay_duration: Optional[int] = 60  # Default 60 minutes
    opening_hours: Optional[str] = None
    vibe_tags: List[str] = []
    image_url: Optional[str] = None

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str  # User Google ID or Guest UUID
    title: str
    summary_text: Optional[str] = None
    representative_image: Optional[str] = None
    places: List[PlaceMetadata]
    survey_snapshot: Optional[dict] = None
    chat_session_id: Optional[str] = None
    share_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PhotoLog(BaseModel):
    url: str  # Local path like /img/uploads/travel_01.jpg
    timestamp: Optional[datetime] = None
    order: int

class TravelLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    place_name: str
    address: Optional[str] = None
    photos: List[PhotoLog]
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
