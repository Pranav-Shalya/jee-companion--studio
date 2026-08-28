import os
import logging
from typing import Optional
import jwt
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Initialize HTTPBearer security scheme
security = HTTPBearer(auto_error=True)

# Cache JWK client per issuer to prevent redundant network fetches
_jwk_clients: dict = {}


def _get_jwk_client(issuer: str) -> PyJWKClient:
    clean_issuer = issuer.rstrip("/")
    if clean_issuer not in _jwk_clients:
        jwks_url = f"{clean_issuer}/.well-known/jwks.json"
        _jwk_clients[clean_issuer] = PyJWKClient(jwks_url)
    return _jwk_clients[clean_issuer]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    FastAPI security dependency validating Clerk RS256 JWT tokens
    against Clerk's JWKS public endpoint.
    
    Returns the authenticated user_id ('sub' claim).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    issuer = os.getenv("CLERK_ISSUER_URL", "").strip()

    if not issuer:
        logger.error("CLERK_ISSUER_URL environment variable is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_ISSUER_URL is not configured on server",
        )

    clean_issuer = issuer.rstrip("/")

    try:
        jwk_client = _get_jwk_client(clean_issuer)
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=clean_issuer,
            options={"verify_aud": False},
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing subject claim ('sub')",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return str(user_id)

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as ite:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(ite)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("JWT verification error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
