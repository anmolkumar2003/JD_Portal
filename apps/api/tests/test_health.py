from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient

from app.core.db import get_db
from app.core.redis import get_redis


class FakeSession:
    async def execute(self, *_: Any, **__: Any) -> None:
        return None


class FakeRedis:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    async def ping(self) -> bool:
        if not self.healthy:
            raise ConnectionError("redis unavailable")
        return True


def _override(app: FastAPI, *, redis_healthy: bool) -> None:
    async def fake_db() -> AsyncIterator[FakeSession]:
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_redis] = lambda: FakeRedis(healthy=redis_healthy)


async def test_health_reports_all_components_ok(app: FastAPI, client: AsyncClient) -> None:
    _override(app, redis_healthy=True)

    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert {name: check["status"] for name, check in body["checks"].items()} == {
        "api": "ok",
        "database": "ok",
        "redis": "ok",
    }
    assert response.headers["X-Request-ID"]


async def test_health_returns_503_when_a_dependency_is_down(
    app: FastAPI, client: AsyncClient
) -> None:
    _override(app, redis_healthy=False)

    response = await client.get("/health", headers={"X-Request-ID": "abc-123"})

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["redis"]["status"] == "down"
    assert response.headers["X-Request-ID"] == "abc-123"
