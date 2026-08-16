"""Lightweight API-key authentication.

A single shared API key is intentionally simple: it demonstrates that every
mutating/expensive route is guarded, without the overhead of a full user
system that would be out of scope for this project. Swapping this for
OAuth2/JWT would only mean changing this module.
"""
from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Pass it via the 'X-API-Key' header.",
        )
