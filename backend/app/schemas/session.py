from datetime import datetime
from enum import IntEnum, Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HintTierEnum(IntEnum):
    TIER_1_CONCEPTUAL_NUDGE = 1
    TIER_2_STRUCTURAL_STRATEGY = 2
    TIER_3_DETAILED_WALKTHROUGH = 3


class SubjectEnum(str, Enum):
    PHYSICS = "Physics"
    CHEMISTRY = "Chemistry"
    MATHEMATICS = "Mathematics"


class StudentAttempt(BaseModel):
    attempt_text: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    feedback: Optional[str] = None
    is_on_track: bool = True


class SessionState(BaseModel):
    session_id: str
    subject: SubjectEnum
    topic: Optional[str] = None
    extracted_query: str
    original_image_url: Optional[str] = None
    current_tier: int = 1
    is_resolved: bool = False
    is_out_of_syllabus: bool = False
    out_of_syllabus_reason: Optional[str] = None
    hints_history: List[Dict[str, Any]] = Field(default_factory=list)
    student_attempts: List[StudentAttempt] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
