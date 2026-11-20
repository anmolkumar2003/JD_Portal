import os
from collections.abc import AsyncIterator, Iterator

# Settings are read at import time, so test values must be set before importing the app.
_TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "REDIS_URL": "redis://localhost:6379/15",
    "JWT_SECRET": "test-only-secret",
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_ACCESS_KEY_ID": "test",
    "S3_SECRET_ACCESS_KEY": "test",
}
for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture
def app() -> Iterator[FastAPI]:
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
