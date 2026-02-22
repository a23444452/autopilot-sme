"""Rate limiting middleware using Redis sliding window counter.

Provides per-client rate limiting with an in-memory token bucket fallback
when Redis is unavailable. Limits are enforced per IP address.
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# Default rate limits (requests per window)
DEFAULT_RATE_LIMIT = 60
DEFAULT_WINDOW_SECONDS = 60

# Stricter limits for expensive endpoints
STRICT_RATE_LIMIT = 10
STRICT_WINDOW_SECONDS = 60


@dataclass
class _TokenBucket:
    """Simple token bucket for in-memory rate limiting."""

    tokens: float
    last_refill: float
    limit: int
    window: int

    def consume(self, now: float) -> tuple[bool, int]:
        """Try to consume a token. Returns (allowed, retry_after_seconds)."""
        elapsed = now - self.last_refill
        refill_rate = self.limit / self.window
        self.tokens = min(self.limit, self.tokens + elapsed * refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0

        deficit = 1.0 - self.tokens
        retry_after = max(1, int(deficit / refill_rate))
        return False, retry_after


@dataclass
class _InMemoryLimiter:
    """Thread-safe in-memory rate limiter using token buckets per client."""

    _buckets: dict[str, _TokenBucket] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def check(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Check rate limit. Returns (allowed, retry_after_seconds)."""
        now = time.time()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or bucket.limit != limit or bucket.window != window:
                bucket = _TokenBucket(
                    tokens=float(limit), last_refill=now, limit=limit, window=window
                )
                self._buckets[key] = bucket
            return bucket.consume(now)


_memory_limiter = _InMemoryLimiter()


def _get_client_ip(request: Request) -> str:
    """Extract the client IP, respecting X-Forwarded-For behind a reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


async def _check_rate_limit(
    request: Request,
    limit: int,
    window: int,
    prefix: str,
) -> None:
    """Check rate limit using Redis sliding window.

    Falls back to an in-memory token bucket when Redis is unavailable.
    Raises HTTP 429 if the limit is exceeded.
    """
    try:
        redis = get_redis()
    except RuntimeError:
        logger.warning("Redis unavailable, using in-memory rate limiter")
        client_ip = _get_client_ip(request)
        key = f"ratelimit:{prefix}:{client_ip}"
        allowed, retry_after = _memory_limiter.check(key, limit, window)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        return

    client_ip = _get_client_ip(request)
    key = f"ratelimit:{prefix}:{client_ip}"
    now = time.time()
    window_start = now - window

    pipe = redis.pipeline()
    # Remove expired entries
    pipe.zremrangebyscore(key, 0, window_start)
    # Add current request
    pipe.zadd(key, {str(now): now})
    # Count requests in window
    pipe.zcard(key)
    # Get oldest entry to compute accurate retry_after
    pipe.zrange(key, 0, 0, withscores=True)
    # Set expiry on the key
    pipe.expire(key, window)
    results = await pipe.execute()

    request_count = results[2]

    if request_count > limit:
        oldest_entries = results[3]
        if oldest_entries:
            oldest_timestamp = oldest_entries[0][1]
            retry_after = max(1, int(oldest_timestamp + window - now))
        else:
            retry_after = window
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


async def rate_limit_default(request: Request) -> None:
    """Standard rate limit: 60 requests per 60 seconds."""
    await _check_rate_limit(
        request,
        limit=DEFAULT_RATE_LIMIT,
        window=DEFAULT_WINDOW_SECONDS,
        prefix="default",
    )


async def rate_limit_strict(request: Request) -> None:
    """Strict rate limit for expensive endpoints: 10 requests per 60 seconds."""
    await _check_rate_limit(
        request,
        limit=STRICT_RATE_LIMIT,
        window=STRICT_WINDOW_SECONDS,
        prefix="strict",
    )
