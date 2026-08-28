import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

import json
import logging
import asyncio
import traceback
import datetime
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.services.multi_llm_consensus import multi_llm_consensus_service
from app.schemas.session import SubjectEnum
from app.schemas.hints import HintEscalation
from app.core.database import AsyncSessionLocal
from app.models.chat import ChatSession, ChatMessage
from app.core.redis import SessionStore

logger = logging.getLogger(__name__)

# APIRouter for chat and mentor endpoints
router = APIRouter(tags=["Mentor & Chat"])


async def _background_escalation_warmup(
    session_id: str,
    question_text: str,
    subject: SubjectEnum,
    solution_latex: str,
    initial_tier1: str,
):
    """Generates and caches HintEscalation in the background for a test handoff session."""
    try:
        escalation = await multi_llm_consensus_service.generate_hint_escalation(
            query=question_text,
            subject=subject,
        )
        if session_id in session_store:
            if not escalation.master_solution and solution_latex and solution_latex != "N/A":
                escalation.master_solution = solution_latex
            session_store[session_id]["escalation"] = escalation
            session_store[session_id]["topic"] = escalation.core_topic
            print(f"✅ [WS-MENTOR] Background HintEscalation ready for test handoff session {session_id}")
    except Exception as err:
        logger.warning("Background escalation warmup for handoff error: %s", err)
        if session_id in session_store:
            session_store[session_id]["escalation"] = HintEscalation(
                core_topic=f"{subject.value} Concept",
                complexity_level="JEE Main",
                hint_1_concept=initial_tier1,
                hint_2_structure="Examine the given variables and establish the fundamental governing equations for this setup.",
                hint_3_calculation="Work through the intermediate algebraic substitution using the equations established in Tier 2.",
                master_solution=solution_latex if solution_latex != "N/A" else "Standard solution.",
            )

# ---------------------------------------------------------
# 1. In-Memory Session Manager & History Repository Cache
# ---------------------------------------------------------
INITIAL_SEED_SESSIONS = [
    {
        "session_id": "jee-session-rot-101",
        "title": "Solid Sphere Rolling on Incline",
        "subject": "Physics",
        "topic": "Rotational Dynamics & Pure Rolling",
        "created_at": "2026-08-26T14:30:00Z",
        "current_hint_level": 3,
        "messages": [
            {
                "id": "msg-rot-1",
                "type": "user_question",
                "subject": "Physics",
                "content": "A solid sphere of mass M and radius R rolls without slipping down an inclined plane of angle theta. Find its linear acceleration.",
                "timestamp": "2026-08-26T14:30:00Z",
            },
            {
                "id": "msg-rot-2",
                "type": "hint_1",
                "hintLevel": 1,
                "tierName": "Tier 1: Conceptual Nudge",
                "topic": "Rotational Dynamics & Pure Rolling",
                "complexity": "JEE Main",
                "content": "Recall the pure-rolling condition: $v_{\\text{cm}} = R\\omega$ and $a_{\\text{cm}} = R\\alpha$. The rolling object experiences torque about its center of mass due to static friction $f_s$.",
                "canRequestMore": True,
                "timestamp": "2026-08-26T14:30:05Z",
            },
            {
                "id": "msg-rot-3",
                "type": "hint_2",
                "hintLevel": 2,
                "tierName": "Tier 2: Structural Strategy & Roadmap",
                "topic": "Rotational Dynamics & Pure Rolling",
                "complexity": "JEE Main",
                "content": "1. Set up Newton's second law along the incline: $Mg\\sin\\theta - f_s = Ma_{\\text{cm}}$.\n2. Set up rotational equation about CM: $\\tau_{\\text{cm}} = f_s R = I_{\\text{cm}}\\alpha$.\n3. Use $I_{\\text{cm}} = \\frac{2}{5}MR^2$ and $\\alpha = a_{\\text{cm}}/R$.",
                "canRequestMore": True,
                "timestamp": "2026-08-26T14:31:00Z",
            },
            {
                "id": "msg-rot-4",
                "type": "hint_3",
                "hintLevel": 3,
                "tierName": "Tier 3: Detailed Walkthrough",
                "topic": "Rotational Dynamics & Pure Rolling",
                "complexity": "JEE Main",
                "content": "Substitute $f_s = \\frac{2}{5}Ma_{\\text{cm}}$ into linear motion equation:\n$$Mg\\sin\\theta - \\frac{2}{5}Ma_{\\text{cm}} = Ma_{\\text{cm}}$$\n$$Mg\\sin\\theta = \\frac{7}{5}Ma_{\\text{cm}}$$\n$$a_{\\text{cm}} = \\frac{5}{7}g\\sin\\theta$$",
                "canRequestMore": False,
                "timestamp": "2026-08-26T14:32:00Z",
            },
        ],
    },
    {
        "session_id": "jee-session-thermo-202",
        "title": "Adiabatic Expansion PV^γ Proof",
        "subject": "Chemistry",
        "topic": "Chemical Thermodynamics",
        "created_at": "2026-08-26T16:15:00Z",
        "current_hint_level": 2,
        "messages": [
            {
                "id": "msg-th-1",
                "type": "user_question",
                "subject": "Chemistry",
                "content": "For an adiabatic reversible expansion of an ideal gas, prove that PV^gamma = constant.",
                "timestamp": "2026-08-26T16:15:00Z",
            },
            {
                "id": "msg-th-2",
                "type": "hint_1",
                "hintLevel": 1,
                "tierName": "Tier 1: Conceptual Nudge",
                "topic": "Chemical Thermodynamics",
                "complexity": "JEE Main",
                "content": "For an adiabatic process, $dq = 0$. By the First Law of Thermodynamics: $dU = dq + dw = -P_{ext} dV$.",
                "canRequestMore": True,
                "timestamp": "2026-08-26T16:15:04Z",
            },
            {
                "id": "msg-th-3",
                "type": "hint_2",
                "hintLevel": 2,
                "tierName": "Tier 2: Structural Strategy & Roadmap",
                "topic": "Chemical Thermodynamics",
                "complexity": "JEE Main",
                "content": "1. Use $dU = n C_v dT$ and $P = \\frac{nRT}{V}$.\n2. Equate $n C_v dT = -\\frac{nRT}{V} dV$.\n3. Separate variables: $\\frac{C_v}{R} \\frac{dT}{T} = -\\frac{dV}{V}$. Use $\\gamma = C_p/C_v$ and $C_p - C_v = R$.",
                "canRequestMore": True,
                "timestamp": "2026-08-26T16:16:00Z",
            },
        ],
    },
    {
        "session_id": "jee-session-math-303",
        "title": "Definite Integral King's Rule",
        "subject": "Mathematics",
        "topic": "Integral Calculus & King's Rule",
        "created_at": "2026-08-26T18:45:00Z",
        "current_hint_level": 1,
        "messages": [
            {
                "id": "msg-m-1",
                "type": "user_question",
                "subject": "Mathematics",
                "content": "Evaluate I = \\int_0^{\\pi/2} \\frac{\\sqrt{\\sin x}}{\\sqrt{\\sin x} + \\sqrt{\\cos x}} dx using King's symmetry rule.",
                "timestamp": "2026-08-26T18:45:00Z",
            },
            {
                "id": "msg-m-2",
                "type": "hint_1",
                "hintLevel": 1,
                "tierName": "Tier 1: Conceptual Nudge",
                "topic": "Integral Calculus & King's Rule",
                "complexity": "JEE Main",
                "content": "King's Rule states that $\\int_a^b f(x)dx = \\int_a^b f(a + b - x)dx$. Notice what happens to $\\sin(\\pi/2 - x)$ and $\\cos(\\pi/2 - x)$.",
                "canRequestMore": True,
                "timestamp": "2026-08-26T18:45:05Z",
            },
        ],
    },
]

# In-memory dictionary holding active sessions
session_store: Dict[str, Dict[str, Any]] = {
    s["session_id"]: {
        "session_id": s["session_id"],
        "title": s["title"],
        "subject": s["subject"],
        "topic": s["topic"],
        "query": s["messages"][0]["content"],
        "created_at": s["created_at"],
        "current_hint_level": s["current_hint_level"],
        "messages": s["messages"],
        "escalation": None,
    }
    for s in INITIAL_SEED_SESSIONS
}


# ---------------------------------------------------------
# 2. Fault-Isolated WebSocket Endpoint with SQLite Persistence
# ---------------------------------------------------------
@router.websocket("/ws/mentor/{session_id}")
async def mentor_websocket(websocket: WebSocket, session_id: str):
    """
    Progressive Socratic mentoring WebSocket endpoint with SQLite database persistence.
    - Ensures ChatSession exists in SQLite database upon connection.
    - Persists user doubts as ChatMessage (role='user').
    - Persists HintEscalation & progressive hints as ChatMessage (role='assistant').
    - Non-blocking commit semantics.
    """
    await websocket.accept()
    print(f"\n🔌 [WS-MENTOR] WebSocket connected for session: {session_id}")
    logger.info("Mentor WebSocket connection established for session: %s", session_id)

    # 1. Initialize SQLite ChatSession Record
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            res = await db.execute(stmt)
            existing_session = res.scalar_one_or_none()
            if not existing_session:
                new_session = ChatSession(
                    id=session_id,
                    title=f"JEE Doubt Session ({session_id[:8]})",
                    created_at=datetime.datetime.utcnow(),
                )
                db.add(new_session)
                await db.commit()
                print(f"🗄️ [SQLITE] Created persistent ChatSession record: {session_id}")
    except Exception as db_init_err:
        logger.error("Error creating ChatSession in SQLite: %s", db_init_err)

    # Initial greeting confirmation
    try:
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to JEE AI Mentor. Send your problem statement to begin progressive hint coaching."
        })
    except Exception as init_err:
        print(f"⚠️ [WS-MENTOR] Failed to send initial greeting: {init_err}")
        return

    # Message listening loop with comprehensive fault isolation
    while True:
        try:
            raw_data = await websocket.receive_text()
            print(f"\n📨 [WS-MENTOR] Received Raw Message (Session: {session_id}):\n   {raw_data[:200]}")

            query_text = ""
            subject_val = SubjectEnum.PHYSICS
            incoming_action = None
            incoming_image = None

            try:
                parsed_json = json.loads(raw_data)
                if isinstance(parsed_json, dict):
                    incoming_action = parsed_json.get("action") or parsed_json.get("type")
                    query_text = (
                        parsed_json.get("query")
                        or parsed_json.get("doubt")
                        or parsed_json.get("message")
                        or parsed_json.get("text")
                        or ""
                    ).strip()

                    incoming_image = parsed_json.get("image")
                    if not query_text and incoming_image:
                        query_text = "Please analyze the attached problem diagram and provide progressive hint guidance."

                    subj_str = str(parsed_json.get("subject", "Physics")).strip().capitalize()
                    try:
                        subject_val = SubjectEnum(subj_str)
                    except ValueError:
                        if "chem" in subj_str.lower():
                            subject_val = SubjectEnum.CHEMISTRY
                        elif "math" in subj_str.lower():
                            subject_val = SubjectEnum.MATHEMATICS
                        else:
                            subject_val = SubjectEnum.PHYSICS
                else:
                    query_text = str(raw_data).strip()
            except json.JSONDecodeError:
                query_text = raw_data.strip()

            # Progressive hint & Socratic checkpoint attempt detection
            progressive_triggers = [
                "i need more help",
                "next hint",
                "next",
                "help",
                "more help",
                "give hint",
                "hint",
                "stuck",
                "next tier",
                "step",
                "attempt",
            ]
            is_progressive_request = (
                (incoming_action in ["evaluate_attempt", "check_attempt", "submit_attempt", "next_hint", "more_help", "hint"])
                or any(trig in query_text.lower() for trig in progressive_triggers)
            )

            # Master Solution trigger detection
            solution_triggers = [
                "master solution",
                "full solution",
                "show answer",
                "give answer",
                "reveal solution",
                "solution",
                "direct answer",
            ]
            is_solution_request = (
                (incoming_action in ["master_solution", "solution", "solve"])
                or any(sol_trig in query_text.lower() for sol_trig in solution_triggers)
            )

            # -------------------------------------------------------------
            # Case D: Test Series Resolve with Mentor State Handoff
            # -------------------------------------------------------------
            if incoming_action == "test_handoff" or (isinstance(parsed_json, dict) and parsed_json.get("action") == "test_handoff"):
                payload_data = parsed_json.get("payload") if isinstance(parsed_json.get("payload"), dict) else parsed_json
                question_text = (
                    payload_data.get("question_text")
                    or payload_data.get("text")
                    or payload_data.get("query")
                    or query_text
                    or ""
                ).strip()
                student_option = str(payload_data.get("student_option") or "Unanswered")
                correct_option = str(payload_data.get("correct_option") or "Correct Answer")
                solution_latex = str(payload_data.get("solution_latex") or payload_data.get("solution") or "N/A")
                subject_str = str(payload_data.get("subject") or subject_val.value)

                try:
                    subject_enum_val = SubjectEnum(subject_str)
                except Exception:
                    subject_enum_val = subject_val

                print(f"\n🎓 [WS-MENTOR] Received Test Series Handoff for session {session_id}:")
                print(f"   • Subject: {subject_str}")
                print(f"   • Question: {question_text[:80]}")
                print(f"   • Student Option: {student_option} vs Correct Option: {correct_option}")

                # Generate custom mentor greeting & Tier-1 Socratic probing question
                mentor_response_text = await multi_llm_consensus_service.generate_test_handoff_mentor_response(
                    question_text=question_text,
                    student_option=student_option,
                    correct_option=correct_option,
                    solution_latex=solution_latex,
                    subject=subject_enum_val,
                )

                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                user_msg_content = f"I took a practice test and selected option **{student_option}** for this question:\n\n{question_text}"
                user_msg = {
                    "id": f"msg-u-handoff-{int(datetime.datetime.now().timestamp() * 1000)}",
                    "type": "user_question",
                    "subject": subject_str,
                    "content": user_msg_content,
                    "timestamp": now_iso,
                }
                hint1_msg = {
                    "id": f"msg-h1-handoff-{int(datetime.datetime.now().timestamp() * 1000) + 1}",
                    "type": "hint_1",
                    "hintLevel": 1,
                    "tierName": "Tier 1: Socratic Mentor Checkpoint",
                    "topic": f"Test Review: {subject_str}",
                    "complexity": "Test Series",
                    "content": mentor_response_text,
                    "canRequestMore": True,
                    "timestamp": now_iso,
                }

                # Start background escalation warmup so subsequent hint tiers work
                asyncio.create_task(
                    _background_escalation_warmup(session_id, question_text, subject_enum_val, solution_latex, mentor_response_text)
                )

                descriptive_title = f"Test Review: {question_text[:40]}..."
                session_store[session_id] = {
                    "session_id": session_id,
                    "title": descriptive_title,
                    "query": question_text,
                    "subject": subject_str,
                    "topic": f"Test Review: {subject_str}",
                    "current_hint_level": 1,
                    "created_at": now_iso,
                    "messages": [user_msg, hint1_msg],
                    "escalation": None,
                }

                # Persist to SessionStore
                try:
                    await SessionStore.save_session(
                        session_id,
                        {
                            "session_id": session_id,
                            "title": descriptive_title,
                            "query": question_text,
                            "subject": subject_str,
                            "current_tier": 1,
                            "student_option": student_option,
                            "correct_option": correct_option,
                            "solution_latex": solution_latex,
                            "created_at": now_iso,
                        }
                    )
                except Exception as store_err:
                    logger.warning("SessionStore save error: %s", store_err)

                # Persist to SQLite ChatSession & ChatMessage
                try:
                    async with AsyncSessionLocal() as db:
                        s_stmt = select(ChatSession).where(ChatSession.id == session_id)
                        s_res = await db.execute(s_stmt)
                        s_obj = s_res.scalar_one_or_none()
                        if s_obj:
                            s_obj.title = descriptive_title
                        else:
                            s_obj = ChatSession(
                                id=session_id,
                                title=descriptive_title,
                                created_at=datetime.datetime.utcnow(),
                            )
                            db.add(s_obj)

                        db_user_msg = ChatMessage(
                            session_id=session_id,
                            role="user",
                            content=user_msg_content,
                            timestamp=datetime.datetime.utcnow(),
                        )
                        db.add(db_user_msg)

                        db_asst_msg = ChatMessage(
                            session_id=session_id,
                            role="assistant",
                            content=json.dumps({
                                "type": "hint_1",
                                "hint_level": 1,
                                "tier_name": "Tier 1: Socratic Mentor Checkpoint",
                                "topic": f"Test Review: {subject_str}",
                                "content": mentor_response_text,
                            }),
                            timestamp=datetime.datetime.utcnow(),
                        )
                        db.add(db_asst_msg)
                        await db.commit()
                        print(f"🗄️ [SQLITE] Saved Test Handoff session & messages to SQLite for {session_id}")
                except Exception as db_err:
                    logger.error("Error saving Test Handoff to SQLite: %s", db_err)

                print(f"📡 [WS-MENTOR] Streaming Mentor Handoff response back to client for session {session_id}...")
                await websocket.send_json({
                    "type": "hint_update",
                    "session_id": session_id,
                    "hint_level": 1,
                    "tier_name": "Tier 1: Socratic Mentor Checkpoint",
                    "topic": f"Test Review: {subject_str}",
                    "complexity": "Test Series",
                    "content": mentor_response_text,
                    "can_request_more": True,
                    "message": f"Active Mentor handoff initiated for {subject_str} test question.",
                })
                continue

            # -------------------------------------------------------------
            # Case A: Master Solution Request
            # -------------------------------------------------------------
            if is_solution_request and session_id in session_store:
                current_session = session_store[session_id]
                escalation: Optional[HintEscalation] = current_session.get("escalation")
                if escalation and escalation.master_solution:
                    current_session["current_hint_level"] = 4
                    solution_msg = {
                        "id": f"msg-sol-{int(datetime.datetime.now().timestamp() * 1000)}",
                        "type": "master_solution",
                        "hintLevel": 4,
                        "tierName": "Master Solution (Verified Math Proof)",
                        "topic": escalation.core_topic,
                        "content": escalation.master_solution,
                        "canRequestMore": False,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    current_session.setdefault("messages", []).append(solution_msg)

                    # Persist Master Solution to SQLite
                    try:
                        async with AsyncSessionLocal() as db:
                            db_msg = ChatMessage(
                                session_id=session_id,
                                role="assistant",
                                content=json.dumps(solution_msg),
                                timestamp=datetime.datetime.utcnow(),
                            )
                            db.add(db_msg)
                            await db.commit()
                    except Exception as db_err:
                        logger.error("Error saving master solution to SQLite: %s", db_err)

                    print(f"🏆 [WS-MENTOR] Master Solution Dispatched for session {session_id}")
                    await websocket.send_json({
                        "type": "master_solution",
                        "session_id": session_id,
                        "topic": escalation.core_topic,
                        "tier_name": "Master Solution (Verified Math Proof)",
                        "content": escalation.master_solution,
                        "message": "Full master solution and proof verification unlocked."
                    })
                    continue

            # -------------------------------------------------------------
            # Case B: Progressive Next-Hint & Socratic Checkpoint Evaluation Request
            # -------------------------------------------------------------
            if is_progressive_request and session_id in session_store:
                current_session = session_store[session_id]
                cur_level = current_session.get("current_hint_level", 1)
                escalation: Optional[HintEscalation] = current_session.get("escalation")

                if not escalation:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No active doubt found in session. Please ask a new question."
                    })
                    continue

                student_attempt_text = parsed_json.get("attempt") or query_text
                is_stuck_request = (
                    not student_attempt_text
                    or any(k in student_attempt_text.lower() for k in ["stuck", "i am stuck", "next hint", "need hint", "help", "more help", "give hint"])
                )

                # 1. If student provided an active step attempt (not just 'stuck'), evaluate it
                if not is_stuck_request and escalation.master_solution:
                    print(f"\n🧐 [WS-MENTOR] Running Socratic Attempt Evaluation for session {session_id} (Tier {cur_level})...")
                    eval_result = await multi_llm_consensus_service.evaluate_student_attempt(
                        attempt=student_attempt_text,
                        current_tier=cur_level,
                        master_proof=escalation.master_solution,
                        rag_context=current_session.get("topic", ""),
                    )

                    is_correct = eval_result.get("is_correct", False)
                    feedback_text = eval_result.get("feedback", "Please review your step.")

                    # Log attempt and feedback to SQLite
                    try:
                        async with AsyncSessionLocal() as db:
                            db_msg = ChatMessage(
                                session_id=session_id,
                                role="assistant",
                                content=json.dumps({
                                    "type": "checkpoint_feedback",
                                    "is_correct": is_correct,
                                    "content": feedback_text,
                                    "feedback": feedback_text,
                                }),
                                timestamp=datetime.datetime.utcnow(),
                            )
                            db.add(db_msg)
                            await db.commit()
                    except Exception as db_err:
                        logger.error("Error saving checkpoint feedback to SQLite: %s", db_err)

                    if not is_correct:
                        # Student is incorrect: Keep on current tier and send feedback string
                        print(f"❌ [WS-MENTOR] Student step incorrect. Keeping at Tier {cur_level}. Feedback: {feedback_text[:80]}")
                        feedback_bubble = {
                            "id": f"msg-fb-{int(datetime.datetime.now().timestamp() * 1000)}",
                            "type": "checkpoint_feedback",
                            "is_correct": False,
                            "tierName": f"Socratic Checkpoint Feedback (Tier {cur_level})",
                            "content": f"⚠️ **Checkpoint Feedback:**\n\n{feedback_text}\n\n*Review the hint above and try adjusting your equation, or click **I am stuck** if you want the next tier roadmap.*",
                            "canRequestMore": True,
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                        current_session.setdefault("messages", []).append(feedback_bubble)

                        await websocket.send_json({
                            "type": "hint_update",
                            "session_id": session_id,
                            "hint_level": cur_level,
                            "tier_name": f"Tier {cur_level} Checkpoint Feedback",
                            "topic": escalation.core_topic,
                            "complexity": escalation.complexity_level,
                            "content": f"⚠️ **Step Feedback:** {feedback_text}\n\nReview the hint above and try adjusting your equation, or click **I am stuck** if you want the next tier roadmap.",
                            "evaluation_feedback": feedback_text,
                            "is_correct": False,
                            "can_request_more": True,
                            "message": f"Step evaluated: Not quite right yet. Feedback: {feedback_text}"
                        })
                        continue

                    print(f"✅ [WS-MENTOR] Student step verified correct! Escalating to next progressive hint tier...")

                # 2. If student is correct or requested next hint / stuck -> Escalate to next tier

                if cur_level == 1:
                    current_session["current_hint_level"] = 2
                    hint_msg = {
                        "id": f"msg-h2-{int(datetime.datetime.now().timestamp() * 1000)}",
                        "type": "hint_2",
                        "hintLevel": 2,
                        "tierName": "Tier 2: Structural Strategy & Roadmap",
                        "topic": escalation.core_topic,
                        "complexity": escalation.complexity_level,
                        "content": escalation.hint_2_structure,
                        "canRequestMore": True,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    current_session.setdefault("messages", []).append(hint_msg)

                    # Persist Tier 2 Hint to SQLite
                    try:
                        async with AsyncSessionLocal() as db:
                            db_msg = ChatMessage(
                                session_id=session_id,
                                role="assistant",
                                content=json.dumps(hint_msg),
                                timestamp=datetime.datetime.utcnow(),
                            )
                            db.add(db_msg)
                            await db.commit()
                    except Exception as db_err:
                        logger.error("Error saving Tier 2 hint to SQLite: %s", db_err)

                    print(f"🪜 [WS-MENTOR] Escalating to Tier 2 for session {session_id}")
                    await websocket.send_json({
                        "type": "hint_update",
                        "session_id": session_id,
                        "hint_level": 2,
                        "tier_name": "Tier 2: Structural Strategy & Roadmap",
                        "topic": escalation.core_topic,
                        "complexity": escalation.complexity_level,
                        "content": escalation.hint_2_structure,
                        "can_request_more": True,
                        "message": f"Escalated to Tier 2 for '{escalation.core_topic}'."
                    })
                elif cur_level == 2:
                    current_session["current_hint_level"] = 3
                    hint_msg = {
                        "id": f"msg-h3-{int(datetime.datetime.now().timestamp() * 1000)}",
                        "type": "hint_3",
                        "hintLevel": 3,
                        "tierName": "Tier 3: Detailed Walkthrough",
                        "topic": escalation.core_topic,
                        "complexity": escalation.complexity_level,
                        "content": escalation.hint_3_calculation,
                        "canRequestMore": False,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    current_session.setdefault("messages", []).append(hint_msg)

                    # Persist Tier 3 Hint to SQLite
                    try:
                        async with AsyncSessionLocal() as db:
                            db_msg = ChatMessage(
                                session_id=session_id,
                                role="assistant",
                                content=json.dumps(hint_msg),
                                timestamp=datetime.datetime.utcnow(),
                            )
                            db.add(db_msg)
                            await db.commit()
                    except Exception as db_err:
                        logger.error("Error saving Tier 3 hint to SQLite: %s", db_err)

                    print(f"🪜 [WS-MENTOR] Escalating to Tier 3 for session {session_id}")
                    await websocket.send_json({
                        "type": "hint_update",
                        "session_id": session_id,
                        "hint_level": 3,
                        "tier_name": "Tier 3: Detailed Walkthrough",
                        "topic": escalation.core_topic,
                        "complexity": escalation.complexity_level,
                        "content": escalation.hint_3_calculation,
                        "can_request_more": False,
                        "message": f"Escalated to Tier 3 for '{escalation.core_topic}'."
                    })
                elif cur_level == 3:
                    current_session["current_hint_level"] = 4
                    solution_msg = {
                        "id": f"msg-sol-{int(datetime.datetime.now().timestamp() * 1000)}",
                        "type": "master_solution",
                        "hintLevel": 4,
                        "tierName": "Master Solution (Verified Math Proof)",
                        "topic": escalation.core_topic,
                        "content": escalation.master_solution,
                        "canRequestMore": False,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    current_session.setdefault("messages", []).append(solution_msg)

                    # Persist Master Solution to SQLite
                    try:
                        async with AsyncSessionLocal() as db:
                            db_msg = ChatMessage(
                                session_id=session_id,
                                role="assistant",
                                content=json.dumps(solution_msg),
                                timestamp=datetime.datetime.utcnow(),
                            )
                            db.add(db_msg)
                            await db.commit()
                    except Exception as db_err:
                        logger.error("Error saving master solution to SQLite: %s", db_err)

                    print(f"🏆 [WS-MENTOR] Tier 3 exhausted. Unlocking Master Solution for session {session_id}")
                    await websocket.send_json({
                        "type": "master_solution",
                        "session_id": session_id,
                        "topic": escalation.core_topic,
                        "tier_name": "Master Solution (Verified Math Proof)",
                        "content": escalation.master_solution,
                        "message": "Tier 3 exhausted. Full Master Solution derivation revealed."
                    })
                else:
                    await websocket.send_json({
                        "type": "info",
                        "message": "All progressive hint tiers and the master solution have already been delivered."
                    })

            # -------------------------------------------------------------
            # Case C: New Dynamic Doubt Submission
            # -------------------------------------------------------------
            else:
                if not query_text:
                    print(f"⚠️ [WS-MENTOR] Received empty query for session {session_id}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Please type or provide a valid doubt question statement."
                    })
                    continue

                print(f"\n🚀 [WS-MENTOR] Ingesting Dynamic Doubt for session {session_id}:")
                print(f"   • Subject: {subject_val.value}")
                print(f"   • Question: {query_text}")

                # Save user message to SQLite
                try:
                    async with AsyncSessionLocal() as db:
                        user_chat_msg = ChatMessage(
                            session_id=session_id,
                            role="user",
                            content=query_text,
                            timestamp=datetime.datetime.utcnow(),
                        )
                        db.add(user_chat_msg)
                        await db.commit()
                except Exception as db_err:
                    logger.error("Error saving user message to SQLite: %s", db_err)

                # Call consensus engine with question, multimodal image & Qdrant RAG
                escalation = await multi_llm_consensus_service.generate_hint_escalation(
                    query=query_text,
                    subject=subject_val,
                    image=incoming_image
                )

                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                user_msg = {
                    "id": f"msg-u-{int(datetime.datetime.now().timestamp() * 1000)}",
                    "type": "user_question",
                    "subject": subject_val.value,
                    "content": query_text,
                    "image": incoming_image,
                    "timestamp": now_iso,
                }
                hint1_msg = {
                    "id": f"msg-h1-{int(datetime.datetime.now().timestamp() * 1000) + 1}",
                    "type": "hint_1",
                    "hintLevel": 1,
                    "tierName": "Tier 1: Conceptual Nudge",
                    "topic": escalation.core_topic,
                    "complexity": escalation.complexity_level,
                    "content": escalation.hint_1_concept,
                    "canRequestMore": True,
                    "timestamp": now_iso,
                }

                # Securely store in session_store with Level 1 and message timeline
                descriptive_title = escalation.core_topic or (query_text[:45] + "..." if len(query_text) > 45 else query_text)
                session_store[session_id] = {
                    "session_id": session_id,
                    "title": descriptive_title,
                    "query": query_text,
                    "image": incoming_image,
                    "subject": subject_val.value,
                    "topic": escalation.core_topic,
                    "escalation": escalation,
                    "current_hint_level": 1,
                    "created_at": now_iso,
                    "messages": [user_msg, hint1_msg],
                }

                # Save generated HintEscalation as JSON string in SQLite ChatMessage
                try:
                    async with AsyncSessionLocal() as db:
                        # Update session title with the classified topic name
                        s_stmt = select(ChatSession).where(ChatSession.id == session_id)
                        s_res = await db.execute(s_stmt)
                        s_obj = s_res.scalar_one_or_none()
                        if s_obj:
                            s_obj.title = descriptive_title
                        else:
                            s_obj = ChatSession(
                                id=session_id,
                                title=descriptive_title,
                                created_at=datetime.datetime.utcnow(),
                            )
                            db.add(s_obj)

                        # Save assistant message with full escalation payload
                        assistant_chat_msg = ChatMessage(
                            session_id=session_id,
                            role="assistant",
                            content=json.dumps({
                                "type": "hint_1",
                                "hint_level": 1,
                                "topic": escalation.core_topic,
                                "complexity": escalation.complexity_level,
                                "content": escalation.hint_1_concept,
                                "hint_1_concept": escalation.hint_1_concept,
                                "hint_2_structure": escalation.hint_2_structure,
                                "hint_3_calculation": escalation.hint_3_calculation,
                                "master_solution": escalation.master_solution,
                            }),
                            timestamp=datetime.datetime.utcnow(),
                        )
                        db.add(assistant_chat_msg)
                        await db.commit()
                        print(f"🗄️ [SQLITE] Saved HintEscalation message to SQLite for session {session_id}")
                except Exception as db_err:
                    logger.error("Error saving HintEscalation message to SQLite: %s", db_err)

                print(f"[WS-MENTOR] Dispatching Tier 1 (Conceptual Nudge) to WebSocket client for session {session_id}...")

                # Send ONLY Tier 1 hint back to client
                await websocket.send_json({
                    "type": "hint_update",
                    "session_id": session_id,
                    "hint_level": 1,
                    "tier_name": "Tier 1: Conceptual Nudge",
                    "topic": escalation.core_topic,
                    "complexity": escalation.complexity_level,
                    "content": escalation.hint_1_concept,
                    "can_request_more": True,
                    "message": f"Tier 1 Conceptual Nudge for '{escalation.core_topic}' activated."
                })

        except WebSocketDisconnect:
            print(f"🔌 [WS-MENTOR] Client disconnected gracefully from session: {session_id}")
            logger.info("Mentor WebSocket disconnected gracefully for session %s", session_id)
            break
        except Exception as exc:
            print(f"❌ [WS-MENTOR ERROR] Exception during WebSocket message handling: {exc.__class__.__name__}: {str(exc)}")
            print(traceback.format_exc())
            logger.error("Resolution error in mentor WebSocket for session %s: %s", session_id, exc)
            try:
                # Send structured resolution error without terminating the connection
                await websocket.send_json({
                    "type": "error",
                    "message": f"Resolution error: {str(exc)}"
                })
            except Exception as send_err:
                print(f"⚠️ [WS-MENTOR] Failed to send error payload to client (socket closed): {send_err}")
                break
