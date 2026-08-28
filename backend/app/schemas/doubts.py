from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.session import SubjectEnum
from app.schemas.hints import HintContent


class DoubtIntakeRequest(BaseModel):
    subject: SubjectEnum
    query_text: Optional[str] = Field(None, description="Typed problem statement or student question")
    image_base64: Optional[str] = Field(None, description="Base64 encoded snapshot of problem or diagram")
    topic_hint: Optional[str] = Field(None, description="Optional student-specified topic")


class OCRResult(BaseModel):
    extracted_text: str
    latex_equations: List[str] = Field(default_factory=list)
    diagram_description: Optional[str] = None
    confidence_score: float = 0.95


class SyllabusValidationResult(BaseModel):
    is_valid_jee: bool
    subject: SubjectEnum
    topic: Optional[str] = None
    syllabus_tier: str = "JEE Advanced & Main"
    flagged_reasons: Optional[str] = None
    jee_redirection_advice: Optional[str] = None


class DoubtIntakeResponse(BaseModel):
    session_id: str
    subject: SubjectEnum
    topic: str
    extracted_query: str
    syllabus_validation: SyllabusValidationResult
    initial_hint: Optional[HintContent] = None
    status_message: str
