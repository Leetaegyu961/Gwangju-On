from pydantic import BaseModel

class UserProfile(BaseModel):
    gender: str
    age: str

class CoursePoint(BaseModel):
    id: str
    type: str
    name: str

class SurveyResult(BaseModel):
    userId: str
    courses: list[CoursePoint]
    themes: list[str]
    companions: list[str]
    budget: list[int]

class OnboardingResponse(BaseModel):
    userId: str
    message: str
