import time
from typing import Optional
from fastapi import Request, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security and anti-sniff headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


async def verify_optional_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[str]:
    """Dependency for optional API key verification."""
    # Local dev allows unauthenticated access by default
    if api_key is None:
        return "dev-guest-user"
    return api_key
