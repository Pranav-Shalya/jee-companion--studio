from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.session import SubjectEnum


class ArtifactType(str, Enum):
    FORMULA_SHEET = "formula_sheet"
    REVISION_NOTE = "revision_note"
    MINDMAP = "mindmap"
    PYQ_BREAKDOWN = "pyq_breakdown"


class ArtifactItem(BaseModel):
    artifact_id: str
    title: str
    subject: SubjectEnum
    topic: str
    artifact_type: ArtifactType
    format: str = "markdown"  # markdown, latex, pdf
    description: str
    content: str
    tags: List[str] = Field(default_factory=list)
    download_filename: str


class TopicResource(BaseModel):
    topic_id: str
    topic_name: str
    subject: SubjectEnum
    subtopics: List[str]
    jee_weightage: str  # High, Medium, Foundational
    recommended_pyqs_count: int
    available_artifacts: List[ArtifactItem] = Field(default_factory=list)


class StudioTopicListResponse(BaseModel):
    subject: Optional[SubjectEnum] = None
    topics: List[TopicResource]


class GenerateArtifactRequest(BaseModel):
    subject: SubjectEnum
    topic: str
    artifact_type: ArtifactType
    custom_focus: Optional[str] = None
