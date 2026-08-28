import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis pool
redis_client: Optional[aioredis.Redis] = None

# In-memory fallback for local dev when Redis is not running
_in_memory_session_store: Dict[str, Dict[str, Any]] = {}


async def init_redis_pool() -> Optional[aioredis.Redis]:
    global redis_client
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await redis_client.ping()
        logger.info("Connected to Redis session store at %s", settings.REDIS_URL)
        return redis_client
    except Exception as exc:
        logger.warning(
            "Could not connect to Redis at %s (%s). Using in-memory session fallback.",
            settings.REDIS_URL,
            exc,
        )
        redis_client = None
        return None


async def close_redis_pool() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Closed Redis connection pool.")


class SessionStore:
    """Async session management for JEE Doubt Resolution state."""

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        global redis_client
        if redis_client:
            try:
                data = await redis_client.get(f"jee_session:{session_id}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error("Redis get error for session %s: %s", session_id, e)
        return _in_memory_session_store.get(session_id)

    @staticmethod
    async def save_session(
        session_id: str, session_data: Dict[str, Any], ttl: int = settings.REDIS_SESSION_TTL_SECONDS
    ) -> bool:
        global redis_client
        _in_memory_session_store[session_id] = session_data
        if redis_client:
            try:
                await redis_client.setex(
                    f"jee_session:{session_id}", ttl, json.dumps(session_data)
                )
                return True
            except Exception as e:
                logger.error("Redis save error for session %s: %s", session_id, e)
                return False
        return True

    @staticmethod
    async def update_hint_tier(
        session_id: str,
        new_tier: int,
        hint_record: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        session = await SessionStore.get_session(session_id)
        if not session:
            return None
        session["current_tier"] = new_tier
        if "hints_history" not in session:
            session["hints_history"] = []
        session["hints_history"].append(hint_record)
        await SessionStore.save_session(session_id, session)
        return session

    @staticmethod
    async def delete_session(session_id: str) -> bool:
        global redis_client
        _in_memory_session_store.pop(session_id, None)
        if redis_client:
            try:
                await redis_client.delete(f"jee_session:{session_id}")
                return True
            except Exception as e:
                logger.error("Redis delete error: %s", e)
                return False
        return True
