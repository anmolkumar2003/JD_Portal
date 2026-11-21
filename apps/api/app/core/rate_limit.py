import inspect
from typing import Any

from fastapi import status
from redis.asyncio import Redis

from app.core.errors import AppError


async def _resolve(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


async def enforce_rate_limit(redis: Redis, key: str, limit: int, window_seconds: int) -> None:
    """Fixed-window counter: the first hit starts the window; hit `limit + 1` gets a 429."""
    count = int(await _resolve(redis.incr(key)))
    if count == 1:
        await _resolve(redis.expire(key, window_seconds))
    if count > limit:
        ttl = int(await _resolve(redis.ttl(key)))
        raise AppError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            "Too many requests. Please try again later.",
            {"retry_after_seconds": max(ttl, 0)},
        )
