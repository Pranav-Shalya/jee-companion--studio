from fastapi import APIRouter
from app.api.v1.doubts import router as doubts_router
from app.api.v1.hints import router as hints_router
from app.api.v1.studio import router as studio_router
from app.api.v1.chat import router as chat_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.tests import router as tests_router
from app.api.v1.analytics import router as analytics_router

api_v1_router = APIRouter()
api_v1_router.include_router(doubts_router)
api_v1_router.include_router(hints_router)
api_v1_router.include_router(studio_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(sessions_router)
api_v1_router.include_router(tests_router)
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
