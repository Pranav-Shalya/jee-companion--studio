from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.test_engine import generate_test_paper

router = APIRouter(prefix="/tests", tags=["Tests"])


class TestRequest(BaseModel):
    subject: str = Field(
        ...,
        description="Subject name: Physics, Chemistry, or Mathematics",
        example="Physics",
    )
    topic: Optional[str] = Field(
        None,
        description="Specific topic or sub-concept filter",
        example="Rotational Dynamics",
    )
    count: int = Field(
        5,
        ge=1,
        le=50,
        description="Number of questions to generate for the test paper",
        example=5,
    )
    difficulty: Optional[str] = Field(
        None,
        description="Exam level: JEE Main or JEE Advanced",
        example="JEE Advanced",
    )
    exam_type: Optional[str] = Field(
        "JEE Mains",
        description="Exam level: JEE Mains or JEE Advanced",
        example="JEE Mains",
    )


@router.post("/generate", response_model=List[Dict[str, Any]])
async def generate_test(request: TestRequest):
    """
    Generates a test series paper using a Hybrid RAG + LLM strategy
    based on subject, topic, difficulty/exam level, and question count.
    """
    try:
        questions = await generate_test_paper(
            subject=request.subject,
            topic=request.topic,
            count=request.count,
            difficulty=request.difficulty,
            exam_type=request.exam_type or request.difficulty or "JEE Mains",
        )
        return questions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test paper: {str(e)}",
        )
