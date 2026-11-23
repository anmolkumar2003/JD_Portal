"""ADM-01: subject-data export is restricted to HR / Super Admin."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Candidate
from tests.conftest import login
from tests.test_apply import _apply, _form

pytestmark = pytest.mark.usefixtures("db")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _candidate_id(db: async_sessionmaker[AsyncSession], email: str) -> str:
    async with db() as session:
        candidate = await session.scalar(select(Candidate).where(Candidate.email == email.lower()))
        assert candidate is not None
        return str(candidate.id)


@pytest.mark.parametrize(
    ("handle", "expected"),
    [
        ("superadmin", 200),
        ("hradmin", 200),
        ("recruiter", 403),
        ("manager", 403),
        ("interviewer", 403),
    ],
)
async def test_candidate_export_admin_only(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    handle: str,
    expected: int,
) -> None:
    email = f"export-{handle}@example.com"
    created = await _apply(client, data=_form(email))
    assert created.status_code == 201, created.text
    candidate_id = await _candidate_id(db, email)

    token = await login(client, handle)
    response = await client.get(
        f"/api/v1/candidates/{candidate_id}/export", headers=_auth(token)
    )

    assert response.status_code == expected
    if expected == 200:
        body = response.json()
        assert body["candidate"]["email"] == email.lower()
        assert "applications" in body
        assert "documents" in body
    else:
        assert response.json()["error"]["code"] == "forbidden"


async def test_candidate_export_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/candidates/00000000-0000-0000-0000-000000000001/export")
    assert response.status_code == 401
