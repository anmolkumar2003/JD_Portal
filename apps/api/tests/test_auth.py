import re
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import DEMO_PASSWORD, login

pytestmark = pytest.mark.usefixtures("db")

AUTH = "/api/v1/auth"


async def test_login_returns_access_token_and_refresh_cookie(client: AsyncClient) -> None:
    response = await client.post(
        f"{AUTH}/login",
        json={"email": "Recruiter@acme.example.com", "password": DEMO_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"  # noqa: S105
    assert body["expires_in"] == 15 * 60
    assert body["user"]["role"] == "recruiter"
    cookie = response.headers["set-cookie"]
    assert "refresh_token=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/v1/auth" in cookie

    me = await client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "recruiter@acme.example.com"


async def test_me_requires_a_token(client: AsyncClient) -> None:
    response = await client.get(f"{AUTH}/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_refresh_rotates_token_and_logout_revokes_it(client: AsyncClient) -> None:
    await login(client, "hradmin")
    old_cookie = client.cookies["refresh_token"]

    refreshed = await client.post(f"{AUTH}/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["user"]["role"] == "hr_admin"
    new_cookie = client.cookies["refresh_token"]
    assert new_cookie != old_cookie

    # Rotation: the previous refresh token can no longer be used.
    client.cookies.clear()
    reused = await client.post(f"{AUTH}/refresh", headers={"Cookie": f"refresh_token={old_cookie}"})
    assert reused.status_code == 401

    current = {"Cookie": f"refresh_token={new_cookie}"}
    assert (await client.post(f"{AUTH}/logout", headers=current)).status_code == 204
    assert (await client.post(f"{AUTH}/refresh", headers=current)).status_code == 401


async def test_account_locks_after_five_failed_logins(client: AsyncClient) -> None:
    creds = {"email": "interviewer@acme.example.com", "password": "wrong-password"}

    statuses = [(await client.post(f"{AUTH}/login", json=creds)).status_code for _ in range(5)]
    assert statuses == [401, 401, 401, 401, 423]

    # The correct password is rejected while the lock is active.
    locked = await client.post(f"{AUTH}/login", json={**creds, "password": DEMO_PASSWORD})
    assert locked.status_code == 423
    assert locked.json()["error"]["code"] == "account_locked"
    assert "locked_until" in locked.json()["error"]["details"]


async def test_unknown_email_gets_the_same_error_as_a_wrong_password(client: AsyncClient) -> None:
    response = await client.post(
        f"{AUTH}/login", json={"email": "nobody@acme.example.com", "password": "x"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_password_reset_round_trip(
    client: AsyncClient,
    sent_emails: list[dict[str, Any]],
    db: async_sessionmaker[AsyncSession],
) -> None:
    response = await client.post(
        f"{AUTH}/forgot-password", json={"email": "manager@acme.example.com"}
    )
    assert response.status_code == 202
    assert len(sent_emails) == 1
    match = re.search(r"(eyJ[\w.-]+)", sent_emails[0]["body"])
    assert match is not None
    token = match.group(1)

    reset = await client.post(
        f"{AUTH}/reset-password", json={"token": token, "new_password": "BrandNew#2026"}
    )
    assert reset.status_code == 200
    await login(client, "manager", "BrandNew#2026")

    reused = await client.post(
        f"{AUTH}/reset-password", json={"token": token, "new_password": "Another#2026"}
    )
    assert reused.status_code == 400


async def test_forgot_password_does_not_reveal_unknown_emails(
    client: AsyncClient, sent_emails: list[dict[str, Any]]
) -> None:
    response = await client.post(
        f"{AUTH}/forgot-password", json={"email": "nobody@acme.example.com"}
    )

    assert response.status_code == 202
    assert sent_emails == []
