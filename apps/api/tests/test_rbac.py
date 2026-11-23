import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.deps import can_access_job, scope_jobs_query
from app.models import Job, User
from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")

USERS = "/api/v1/users"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
async def test_only_admins_can_list_users(client: AsyncClient, handle: str, expected: int) -> None:
    token = await login(client, handle)

    response = await client.get(USERS, headers=_auth(token))

    assert response.status_code == expected
    if expected == 200:
        assert response.json()["total"] == 5
    else:
        assert response.json()["error"]["code"] == "forbidden"


async def test_hr_admin_creates_user_and_changes_role(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    created = await client.post(
        USERS,
        headers=_auth(token),
        json={
            "email": "new.recruiter@demo.example.com",
            "full_name": "New Recruiter",
            "role": "recruiter",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["user"]["must_change_password"] is True
    assert len(body["temporary_password"]) >= 12
    user_id = body["user"]["id"]

    changed = await client.patch(
        f"{USERS}/{user_id}/role", headers=_auth(token), json={"role": "hr_admin"}
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "hr_admin"

    legacy = await client.patch(
        f"{USERS}/{user_id}/role", headers=_auth(token), json={"role": "hiring_manager"}
    )
    assert legacy.status_code == 422


async def test_hr_admin_cannot_grant_super_admin(client: AsyncClient) -> None:
    token = await login(client, "hradmin")
    users = (await client.get(USERS, headers=_auth(token))).json()["items"]
    recruiter_id = next(u["id"] for u in users if u["role"] == "recruiter")

    response = await client.patch(
        f"{USERS}/{recruiter_id}/role", headers=_auth(token), json={"role": "super_admin"}
    )

    assert response.status_code == 403


async def test_recruiter_cannot_change_roles(client: AsyncClient) -> None:
    admin_token = await login(client, "hradmin")
    users = (await client.get(USERS, headers=_auth(admin_token))).json()["items"]
    interviewer_id = next(u["id"] for u in users if u["role"] == "interviewer")
    token = await login(client, "recruiter")

    response = await client.patch(
        f"{USERS}/{interviewer_id}/role", headers=_auth(token), json={"role": "hr_admin"}
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("handle", "visible_slugs"),
    [
        ("recruiter", {"senior-android-developer", "shopify-developer", "content-writer"}),
        ("manager", {"senior-android-developer", "shopify-developer"}),
        ("interviewer", {"senior-android-developer"}),
    ],
)
async def test_record_level_job_access(
    db: async_sessionmaker[AsyncSession], handle: str, visible_slugs: set[str]
) -> None:
    async with db() as session:
        user = await session.scalar(select(User).where(User.email.startswith(f"{handle}@")))
        assert user is not None

        slugs = set(await session.scalars(scope_jobs_query(user, select(Job.slug))))
        assert slugs == visible_slugs

        hr_job = await session.scalar(select(Job).where(Job.slug == "content-writer"))
        assert hr_job is not None
        assert await can_access_job(session, user, hr_job.id) is (handle == "recruiter")
