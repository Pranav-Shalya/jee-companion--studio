import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.hints import (
    ProgressiveHintRequest,
    ProgressiveHintResponse,
    StudentAttemptRequest,
    StudentAttemptResponse,
)
from app.schemas.session import SubjectEnum
from app.core.redis import SessionStore
from app.core.security import verify_optional_api_key
from app.services.guardrails import guardrails_service
from app.services.rag_engine import rag_engine_service
from app.services.multi_llm_consensus import multi_llm_consensus_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hints", tags=["Progressive Hints"])


@router.post("/progress", response_model=ProgressiveHintResponse)
async def progress_hint_tier(
    request: ProgressiveHintRequest,
    user: str = Depends(verify_optional_api_key),
):
    """
    Unlocks next tier hint (Tier 2 or Tier 3).
    Ensures strict progressive order: Tier 1 -> Tier 2 -> Tier 3.
    """
    session = await SessionStore.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active doubt session {request.session_id} not found.",
        )

    current_tier = session.get("current_tier", 1)
    target_tier = request.target_tier

    # Enforce progressive pacing: student can only jump to current + 1
    if target_tier > current_tier + 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please review Tier {current_tier + 1} before proceeding to higher tiers.",
        )

    subject_val = SubjectEnum(session.get("subject", "Physics"))
    query = session.get("extracted_query", "")

    # Retrieve context
    rag_context = await rag_engine_service.retrieve_context(query, subject_val)

    # Multi-LLM consensus synthesis for target hint tier
    hint = await multi_llm_consensus_service.generate_progressive_hint(
        query=query,
        subject=subject_val,
        target_tier=target_tier,
        context_chunks=rag_context,
        student_previous_attempt=request.student_notes,
    )
    hint = guardrails_service.enforce_hint_tier_guardrails(hint)

    # Update session state in Redis
    updated_session = await SessionStore.update_hint_tier(
        session_id=request.session_id,
        new_tier=target_tier,
        hint_record=hint.model_dump(mode="json"),
    )

    is_resolved = target_tier >= 3

    return ProgressiveHintResponse(
        session_id=request.session_id,
        hint=hint,
        session_resolved=is_resolved,
        message=f"Tier {target_tier} unlocked successfully.",
    )


@router.post("/attempt", response_model=StudentAttemptResponse)
async def submit_student_attempt(
    request: StudentAttemptRequest,
    user: str = Depends(verify_optional_api_key),
):
    """
    Evaluates student's intermediate calculation step or thought process.
    Provides targeted Socratic hints without solving the problem outright.
    """
    session = await SessionStore.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found.",
        )

    current_tier = session.get("current_tier", 1)
    query = session.get("extracted_query", "")

    evaluation = await multi_llm_consensus_service.evaluate_student_attempt(
        session_id=request.session_id,
        query=query,
        attempt_text=request.student_attempt_text,
        current_tier=current_tier,
    )

    # Append student attempt to session
    attempt_entry = {
        "attempt_text": request.student_attempt_text,
        "submitted_at": datetime.utcnow().isoformat(),
        "feedback": evaluation["feedback"],
        "is_on_track": evaluation["is_on_track"],
    }
    if "student_attempts" not in session:
        session["student_attempts"] = []
    session["student_attempts"].append(attempt_entry)
    await SessionStore.save_session(request.session_id, session)

    return StudentAttemptResponse(
        session_id=request.session_id,
        is_on_track=evaluation["is_on_track"],
        feedback=evaluation["feedback"],
        socratic_guidance=evaluation["socratic_guidance"],
        recommended_action=evaluation["recommended_action"],
    )
