from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any

from app.services.analytics_engine import log_test_event, get_student_dashboard
from app.core.auth import get_current_user

router = APIRouter()


class TestEventRequest(BaseModel):
    user_id: str = Field(..., description="Unique student or user identifier", example="student_123")
    subject: str = Field(..., description="JEE Subject: Physics, Chemistry, or Mathematics", example="Physics")
    topic: str = Field(..., description="Topic name evaluated", example="Rotational Dynamics")
    score: float = Field(..., description="Test score percentage (0.0 - 100.0)", example=85.0)
    difficulty: float = Field(default=1.0, description="Question difficulty multiplier (e.g. 1.0 for Mains, 1.2 for Advanced)", example=1.0)


@router.post("/log", status_code=status.HTTP_201_CREATED, summary="Log a completed test event for spaced repetition")
async def log_event(
    request: TestEventRequest,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Logs a student's test score event into the Analytics database,
    derives memory strength S, and schedules the next review date based on
    the Ebbinghaus Forgetting Curve targeting R = 0.70 retention.
    """
    if request.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot log test events on behalf of another user",
        )

    try:
        logged_data = log_test_event(
            user_id=request.user_id,
            subject=request.subject,
            topic=request.topic,
            score=request.score,
            difficulty=request.difficulty,
        )
        return {
            "status": "success",
            "message": "Test event logged successfully",
            "data": logged_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log test event: {str(e)}",
        )


@router.get("/{user_id}/dashboard", summary="Fetch student spaced repetition dashboard and momentum analytics")
async def student_dashboard(
    user_id: str,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Queries historical test events for the given user_id and returns:
    - total_tests_taken: Count grouped by subject.
    - moving_average: Arithmetic average score percentage of the last 5 tests.
    - action_queue: Topics where next_review_date <= current_time, ordered by most overdue.
    - mastery_matrix: Live Ebbinghaus retention matrix across all tracked topics.
    """
    if user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access another user's analytics dashboard",
        )

    try:
        dashboard_data = get_student_dashboard(user_id)
        return dashboard_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve student dashboard: {str(e)}",
        )
