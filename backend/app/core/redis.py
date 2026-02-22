"""Async Redis connection manager using app.state instead of global mutable state."""

import redis.asyncio as aioredis
from fastapi import Request

from app.core.config import settings


async def init_redis(app_state: object) -> aioredis.Redis:
    """Initialize the async Redis connection and store it on app.state."""
    client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )
    # Verify connectivity
    await client.ping()
    app_state.redis = client  # type: ignore[attr-defined]
    return client


async def close_redis(app_state: object) -> None:
    """Close the Redis connection stored on app.state."""
    client: aioredis.Redis | None = getattr(app_state, "redis", None)
    if client is not None:
        await client.aclose()
        app_state.redis = None  # type: ignore[attr-defined]


def get_redis_from_app(request: Request) -> aioredis.Redis:
    """FastAPI dependency that returns the Redis client from app.state."""
    client: aioredis.Redis | None = getattr(request.app.state, "redis", None)
    if client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return client


def get_redis() -> aioredis.Redis:
    """Backward-compatible accessor for non-request contexts (e.g. rate limiter).

    Falls back to the module-level _fallback_client which is set during init.
    Prefer get_redis_from_app for request-scoped access.
    """
    if _fallback_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _fallback_client


_fallback_client: aioredis.Redis | None = None


async def init_redis_compat(app_state: object) -> aioredis.Redis:
    """Initialize Redis and set both app.state and module fallback."""
    global _fallback_client
    client = await init_redis(app_state)
    _fallback_client = client
    return client


async def close_redis_compat(app_state: object) -> None:
    """Close Redis and clear both app.state and module fallback."""
    global _fallback_client
    await close_redis(app_state)
    _fallback_client = None
