from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class GoalIn(BaseModel):
    level: str = Field(description="year|month|week|day")
    title: str
    metric: Optional[str] = None
    target: Optional[float] = None
    deadline: Optional[date] = None
    parent_goal_id: Optional[int] = None
    weight: float = 1.0

class GoalOut(BaseModel):
    id: int
    level: str
    title: str
    status: str
    class Config: from_attributes = True

class TaskIn(BaseModel):
    title: str
    due: Optional[date] = None
    estimate_min: Optional[int] = None
    goal_id: Optional[int] = None

class TaskOut(BaseModel):
    id: int
    title: str
    status: str
    class Config: from_attributes = True

class NewsPrefsIn(BaseModel):
    topics: List[str]

class MorningReport(BaseModel):
    schedule: str
    free_blocks: List[str]
    weather: str
    headlines: List[str]
    top3_priorities: List[str]

class QuizQ(BaseModel):
    question: str
    choices: Optional[List[str]] = None
    answer: str
    explanation: Optional[str] = None
    page_ref: Optional[str] = None

class QuizOut(BaseModel):
    questions: List[QuizQ]
