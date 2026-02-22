"""Authentication dependencies for API routes.

Provides API Key authentication via the X-API-Key header.
When API_KEY is not configured (empty string), authentication is disabled
to allow development without credentials.
"""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(
    name=settings.API_KEY_HEADER,
    auto_error=False,
)


async def verify_api_key(
    api_key: Annotated[str | None, Security(_api_key_header)] = None,
) -> str:
    """Validate the API key from the request header.

    Raises HTTP 401 if the key is missing and HTTP 403 if invalid.
    Returns the validated API key string.

    When ``settings.API_KEY`` is empty, authentication is skipped
    (development mode).
    """
    if not settings.API_KEY:
        return "dev-no-auth"

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


RequireAuth = Depends(verify_api_key)
