import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables at the very top before any service or config imports
load_dotenv(find_dotenv())

import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.redis import init_redis_pool, close_redis_pool, SessionStore
from app.core.security import SecurityHeadersMiddleware
from app.api.v1.router import api_v1_router
from app.api.v1.chat import router as chat_router
from app.api.v1 import analytics
from app.services.rag_engine import rag_engine_service
from app.services.multi_llm_consensus import multi_llm_consensus_service
from app.services.guardrails import guardrails_service
from app.services.analytics_engine import init_analytics_db
from app.schemas.session import SubjectEnum

from app.core.database import Base, engine
from app.models.chat import ChatSession, ChatMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jee_doubt_solver")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing JEE Doubt Solver Backend Services...")
    await init_redis_pool()
    await rag_engine_service.initialize_client()
    
    # Initialize SQLite database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("SQLite database tables initialized successfully.")
    
    # Initialize Analytics database tables (Forgetting curve spaced repetition)
    init_analytics_db()
    logger.info("Analytics SQLite database (test_events) initialized successfully.")
    
    logger.info("Startup complete. System ready for progressive hint resolution.")
    yield
    logger.info("Shutting down backend services...")
    await close_redis_pool()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="JEE Main & Advanced Progressive Doubt Resolution and Companion Studio API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup_event():
    """Startup event to initialize SQLite database tables via run_sync and analytics DB."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    init_analytics_db()
    logger.info("SQLite schema & Analytics DB initialized via startup event.")

# CORS middleware configuration with full Vercel, Render, and development origin support
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://jee-companion-studio.vercel.app",
    "https://jee-companion-studio-yh78.vercel.app",
]

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount API V1 router, Analytics router, and Chat/WebSocket router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(chat_router)  # Provides /ws/mentor/{session_id} and root routes


@app.get("/", tags=["Health & Meta"])
async def root_status():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "syllabus_guardrails": "Enforced (JEE Main/Advanced)",
        "hint_protocol": "3-Tier Progressive Scaffolding (Groq + Gemini Consensus)",
    }


@app.get("/health", tags=["Health & Meta"])
async def health_check():
    return {"status": "healthy"}


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time interactive Socratic coaching,
    live hint streaming, and step-by-step evaluation.
    """
    await websocket.accept()
    logger.info("WebSocket connected for session %s", session_id)
    try:
        # Send initial confirmation
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "message": "Connected to JEE Socratic Coaching Engine"
        })

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg_type = payload.get("type")

            if msg_type == "request_hint":
                target_tier = payload.get("target_tier", 1)
                session = await SessionStore.get_session(session_id)
                if not session:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Session not found"
                    })
                    continue

                subject = SubjectEnum(session.get("subject", "Physics"))
                query = session.get("extracted_query", "")

                hint = await multi_llm_consensus_service.generate_progressive_hint(
                    query=query,
                    subject=subject,
                    target_tier=target_tier
                )
                hint = guardrails_service.enforce_hint_tier_guardrails(hint)

                await SessionStore.update_hint_tier(session_id, target_tier, hint.model_dump(mode="json"))

                await websocket.send_json({
                    "type": "hint_update",
                    "session_id": session_id,
                    "hint": hint.model_dump(mode="json"),
                    "resolved": target_tier >= 3
                })

            elif msg_type == "submit_step":
                step_text = payload.get("step_text", "")
                session = await SessionStore.get_session(session_id)
                current_tier = session.get("current_tier", 1) if session else 1
                query = session.get("extracted_query", "") if session else ""

                eval_result = await multi_llm_consensus_service.evaluate_student_attempt(
                    session_id=session_id,
                    query=query,
                    attempt_text=step_text,
                    current_tier=current_tier
                )

                await websocket.send_json({
                    "type": "step_feedback",
                    "session_id": session_id,
                    "feedback": eval_result
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as e:
        logger.error("WebSocket error for session %s: %s", session_id, e)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
