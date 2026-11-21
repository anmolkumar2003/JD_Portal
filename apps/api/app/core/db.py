from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _sync_database_url(async_url: str) -> str:
    """Celery workers use sync SQLAlchemy; swap asyncpg for psycopg."""
    if "+asyncpg" in async_url:
        return async_url.replace("+asyncpg", "+psycopg", 1)
    if async_url.startswith("postgresql://"):
        return async_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return async_url


sync_engine: Engine = create_engine(
    _sync_database_url(get_settings().database_url), pool_pre_ping=True
)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@contextmanager
def sync_session() -> Iterator[Session]:
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
