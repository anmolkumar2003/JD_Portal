import inspect
from typing import Any

from fastapi import status
from redis.asyncio import Redis

from app.core.errors import AppError


async def resolve(value: Any) -> Any:
    """redis-py types commands as sync-or-async; the asyncio client always returns awaitables."""
    return await value if inspect.isawaitable(value) else value


async def enforce_rate_limit(redis: Redis, key: str, limit: int, window_seconds: int) -> None:
    """Fixed-window counter: the first hit starts the window; hit `limit + 1` gets a 429."""
    count = int(await resolve(redis.incr(key)))
    if count == 1:
        await resolve(redis.expire(key, window_seconds))
    if count > limit:
        ttl = int(await resolve(redis.ttl(key)))
        raise AppError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            "Too many requests. Please try again later.",
            {"retry_after_seconds": max(ttl, 0)},
        )
