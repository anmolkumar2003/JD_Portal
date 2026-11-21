import asyncio
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health import ComponentStatus, HealthChecks, HealthResponse

CHECK_TIMEOUT_SECONDS = 2.0

logger = logging.getLogger(__name__)


async def _timed(name: str, probe: Callable[[], Awaitable[Any]]) -> ComponentStatus:
    start = time.perf_counter()
    try:
        await asyncio.wait_for(probe(), timeout=CHECK_TIMEOUT_SECONDS)
    except Exception:
        logger.warning("health check failed", extra={"component": name}, exc_info=True)
        return ComponentStatus(status="down")
    return ComponentStatus(status="ok", latency_ms=round((time.perf_counter() - start) * 1000, 2))


async def check_database(session: AsyncSession) -> ComponentStatus:
    return await _timed("database", lambda: session.execute(text("SELECT 1")))


async def check_redis(client: Redis) -> ComponentStatus:
    async def probe() -> None:
        # redis-py types ping() as sync-or-async; the asyncio client always returns an awaitable.
        result = client.ping()
        if inspect.isawaitable(result):
            await result

    return await _timed("redis", probe)


async def get_health(session: AsyncSession, redis_client: Redis, version: str) -> HealthResponse:
    database, redis = await asyncio.gather(check_database(session), check_redis(redis_client))
    checks = HealthChecks(api=ComponentStatus(status="ok"), database=database, redis=redis)
    healthy = database.status == "ok" and redis.status == "ok"
    return HealthResponse(status="ok" if healthy else "degraded", version=version, checks=checks)
