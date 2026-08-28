import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.models.chat import ChatSession, ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sessions & History"])


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """
    Returns all ChatSession records from SQLite, ordered by latest created_at.
    """
    try:
        stmt = select(ChatSession).order_by(ChatSession.created_at.desc())
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "session_id": s.id,
                "title": s.title or f"JEE Doubt Session ({s.id[:8]})",
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "subject": "Physics",
            }
            for s in sessions
        ]
    except Exception as e:
        logger.error("Error retrieving sessions from SQLite database: %s", e)
        return []


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns all ChatMessage records for a specific session.
    """
    session_stmt = select(ChatSession).where(ChatSession.id == session_id)
    s_res = await db.execute(session_stmt)
    session_obj = s_res.scalar_one_or_none()

    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found.",
        )

    msg_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()

    formatted_messages = []
    for m in messages:
        try:
            content_json = json.loads(m.content)
            if isinstance(content_json, dict) and ("type" in content_json or "hint_1_concept" in content_json):
                formatted_messages.append({
                    "id": f"msg-{m.id}",
                    "type": content_json.get("type", "hint_1" if m.role == "assistant" else "user_question"),
                    "hintLevel": content_json.get("hintLevel") or content_json.get("hint_level", 1),
                    "tierName": content_json.get("tierName") or content_json.get("tier_name"),
                    "topic": content_json.get("topic"),
                    "complexity": content_json.get("complexity"),
                    "content": content_json.get("content") or content_json.get("hint_1_concept") or str(content_json),
                    "canRequestMore": content_json.get("canRequestMore", True),
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                })
            else:
                formatted_messages.append({
                    "id": f"msg-{m.id}",
                    "type": "user_question" if m.role == "user" else "hint_1",
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                })
        except Exception:
            formatted_messages.append({
                "id": f"msg-{m.id}",
                "type": "user_question" if m.role == "user" else "hint_1",
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            })

    return {
        "session_id": session_obj.id,
        "title": session_obj.title or f"JEE Doubt Session ({session_obj.id[:8]})",
        "created_at": session_obj.created_at.isoformat() if session_obj.created_at else None,
        "messages": formatted_messages,
    }


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Deletes a session and all its associated messages from the SQLite database.
    - Manually deletes all ChatMessage records for the session to prevent database orphans.
    - Deletes the ChatSession record.
    - Commits the transaction.
    """
    try:
        # 1. Verify existence of the session
        check_stmt = select(ChatSession).where(ChatSession.id == session_id)
        res = await db.execute(check_stmt)
        session_obj = res.scalar_one_or_none()

        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID '{session_id}' not found.",
            )

        # 2. Delete all child ChatMessage records matching the session_id
        delete_messages_stmt = delete(ChatMessage).where(ChatMessage.session_id == session_id)
        await db.execute(delete_messages_stmt)

        # 3. Delete the parent ChatSession record
        delete_session_stmt = delete(ChatSession).where(ChatSession.id == session_id)
        await db.execute(delete_session_stmt)

        # 4. Commit the transaction
        await db.commit()
        logger.info("Successfully deleted session %s and associated messages from SQLite.", session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting session %s: %s", session_id, e)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )
