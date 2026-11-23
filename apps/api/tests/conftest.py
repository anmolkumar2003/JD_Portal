import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

# Settings are read at import time, so test values must be set before importing the app.
_TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "REDIS_URL": "redis://localhost:6379/15",
    "JWT_SECRET": "test-only-secret",
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_ACCESS_KEY_ID": "test",
    "S3_SECRET_ACCESS_KEY": "test",
    "API_RATE_LIMIT_PER_MINUTE": "0",
    # Optional modules keep their own tests (and public apply is the quickest way to create
    # applications); test_org_settings.py covers the default, switched-off behaviour.
    "ENABLE_PUBLIC_CAREERS": "true",
    "ENABLE_INTERVIEWS": "true",
    "ENABLE_OFFERS": "true",
    "ENABLE_REQUISITIONS": "true",
    "ENABLE_AUDIT_UI": "true",
}
for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import make_url, text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import get_db  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models import Base  # noqa: E402
from app.seed_demo import DEMO_EMAIL_DOMAIN, seed  # noqa: E402

# Generated-looking but fixed so tests are reproducible; only ever used in the test database.
DEMO_PASSWORD = "Tq7!test-fixture-pw"  # noqa: S105
__all__ = ["DEMO_EMAIL_DOMAIN", "DEMO_PASSWORD", "login"]

_schema_ready = False


@pytest.fixture
def app() -> Iterator[FastAPI]:
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# --- Database-backed fixtures -----------------------------------------------------------------


class FakeRedis:
    """Just enough of redis.asyncio.Redis for token revocation and rate limiting."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self.store[name] = value
        return True

    async def exists(self, *names: str) -> int:
        return sum(name in self.store for name in names)

    async def incr(self, name: str) -> int:
        value = int(self.store.get(name, "0")) + 1
        self.store[name] = str(value)
        return value

    async def expire(self, name: str, seconds: int) -> bool:
        return name in self.store

    async def ttl(self, name: str) -> int:
        return 3600 if name in self.store else -2


def _test_database_url() -> str:
    """A separate `<db>_test` database on the same server, so dev data is never touched."""
    url = make_url(get_settings().database_url)
    return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


async def _prepare_schema(url: str) -> None:
    global _schema_ready  # noqa: PLW0603
    if _schema_ready:
        return
    target = make_url(url)
    admin = create_async_engine(
        target.set(database="postgres"), poolclass=NullPool, isolation_level="AUTOCOMMIT"
    )
    async with admin.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target.database}
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    await admin.dispose()

    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    _schema_ready = True


@pytest.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    url = _test_database_url()
    try:
        await _prepare_schema(url)
    except OSError as exc:
        pytest.skip(f"Postgres not reachable for DB tests: {exc}")
    engine = create_async_engine(url, poolclass=NullPool)
    yield engine
    async with engine.begin() as conn:
        tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    await engine.dispose()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
async def db(
    app: FastAPI, db_engine: AsyncEngine, fake_redis: FakeRedis
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Point the app at the test database, seeded with the demo org, users and jobs."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with factory() as session:
        await seed(session, password=DEMO_PASSWORD)
    yield factory


@pytest.fixture(autouse=True)
def _no_real_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never write to the real bucket (this is how stub CVs piled up before)."""

    async def put_object(key: str, data: bytes, content_type: str) -> None:
        return None

    async def delete_object(key: str) -> None:
        return None

    monkeypatch.setattr("app.core.storage.put_object", put_object)
    monkeypatch.setattr("app.core.storage.delete_object", delete_object)


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    class _Task:
        @staticmethod
        def delay(to: str, subject: str, body: str) -> None:
            sent.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr("app.services.auth.send_email", _Task)
    monkeypatch.setattr("app.services.applications.send_email", _Task)
    return sent


@pytest.fixture
def stored_objects(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """In-memory stand-in for MinIO uploads."""
    objects: dict[str, bytes] = {}

    async def put_object(key: str, data: bytes, content_type: str) -> None:
        objects[key] = data

    async def delete_object(key: str) -> None:
        objects.pop(key, None)

    monkeypatch.setattr("app.core.storage.put_object", put_object)
    monkeypatch.setattr("app.core.storage.delete_object", delete_object)
    return objects


async def login(client: AsyncClient, handle: str, password: str = DEMO_PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": f"{handle}@{DEMO_EMAIL_DOMAIN}", "password": password},
    )
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token
