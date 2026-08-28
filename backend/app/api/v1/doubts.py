import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.doubts import (
    DoubtIntakeRequest,
    DoubtIntakeResponse,
)
from app.schemas.session import SessionState
from app.core.redis import SessionStore
from app.core.security import verify_optional_api_key
from app.services.vision_ocr import vision_ocr_service
from app.services.guardrails import guardrails_service
from app.services.rag_engine import rag_engine_service
from app.services.multi_llm_consensus import multi_llm_consensus_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/doubts", tags=["Doubt Intake & Resolution"])


@router.post("/intake", response_model=DoubtIntakeResponse, status_code=status.HTTP_201_CREATED)
async def intake_doubt(
    request: DoubtIntakeRequest,
    user: str = Depends(verify_optional_api_key),
):
    """
    Intake endpoint for JEE problems (Text and/or Image).
    Performs OCR if image is supplied, enforces JEE syllabus boundaries,
    and returns the Tier 1 Conceptual Nudge without revealing direct answers.
    """
    session_id = f"jee-{uuid.uuid4().hex[:10]}"
    extracted_query = request.query_text or ""

    # 1. Process image OCR if provided
    if request.image_base64:
        ocr_result = await vision_ocr_service.process_image(
            request.image_base64, subject_hint=request.subject.value
        )
        if not extracted_query:
            extracted_query = ocr_result.extracted_text
        else:
            extracted_query = f"{extracted_query}\n[Image Extracted Text]: {ocr_result.extracted_text}"

    if not extracted_query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a problem statement or an image snapshot of the doubt.",
        )

    # 2. Syllabus Boundary Validation
    syllabus_val = guardrails_service.validate_syllabus(
        extracted_query, request.subject
    )

    if not syllabus_val.is_valid_jee:
        session_data = SessionState(
            session_id=session_id,
            subject=request.subject,
            topic=request.topic_hint or "Out of Syllabus",
            extracted_query=extracted_query,
            current_tier=1,
            is_out_of_syllabus=True,
            out_of_syllabus_reason=syllabus_val.flagged_reasons,
        )
        await SessionStore.save_session(session_id, session_data.model_dump(mode="json"))

        return DoubtIntakeResponse(
            session_id=session_id,
            subject=request.subject,
            topic="Out of Syllabus",
            extracted_query=extracted_query,
            syllabus_validation=syllabus_val,
            initial_hint=None,
            status_message=f"Query flagged: {syllabus_val.flagged_reasons}",
        )

    # 3. RAG Retrieval for context & formulas
    rag_context = await rag_engine_service.retrieve_context(
        extracted_query, request.subject
    )

    # 4. Generate Tier 1: Conceptual Nudge
    initial_hint = await multi_llm_consensus_service.generate_progressive_hint(
        query=extracted_query,
        subject=request.subject,
        target_tier=1,
        context_chunks=rag_context,
    )
    initial_hint = guardrails_service.enforce_hint_tier_guardrails(initial_hint)

    # 5. Persist Session State in Redis
    session_data = SessionState(
        session_id=session_id,
        subject=request.subject,
        topic=request.topic_hint or "Kinematics & Dynamics",
        extracted_query=extracted_query,
        current_tier=1,
        hints_history=[initial_hint.model_dump(mode="json")],
        created_at=datetime.utcnow(),
    )
    await SessionStore.save_session(session_id, session_data.model_dump(mode="json"))

    return DoubtIntakeResponse(
        session_id=session_id,
        subject=request.subject,
        topic=session_data.topic or "JEE Topic",
        extracted_query=extracted_query,
        syllabus_validation=syllabus_val,
        initial_hint=initial_hint,
        status_message="Doubt ingested successfully. Tier 1 Conceptual Nudge activated.",
    )


@router.get("/{session_id}", response_model=SessionState)
async def get_doubt_session(
    session_id: str,
    user: str = Depends(verify_optional_api_key),
):
    """Retrieve full session state and history."""
    session = await SessionStore.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doubt session {session_id} not found.",
        )
    return session
