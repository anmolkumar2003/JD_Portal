from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import DEMO_EMAIL_DOMAIN, DEMO_PASSWORD, login

pytestmark = pytest.mark.usefixtures("db")

AUTH = "/api/v1/auth"
USERS = "/api/v1/users"
NEW_PASSWORD = "Fresh-Start#2026x"  # noqa: S105


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create(client: AsyncClient, token: str, **overrides: Any) -> dict[str, Any]:
    payload = {"email": "temp.user@example.com", "full_name": "Temp User", "role": "recruiter"}
    response = await client.post(USERS, headers=_auth(token), json={**payload, **overrides})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_temporary_password_forces_a_change_before_anything_else(
    client: AsyncClient,
) -> None:
    admin = await login(client, "hradmin")
    created = await _create(client, admin)
    email, temporary = created["user"]["email"], created["temporary_password"]

    signed_in = await client.post(f"{AUTH}/login", json={"email": email, "password": temporary})
    assert signed_in.status_code == 200
    assert signed_in.json()["user"]["must_change_password"] is True
    token = signed_in.json()["access_token"]

    assert (await client.get(f"{AUTH}/me", headers=_auth(token))).status_code == 200
    blocked = await client.get("/api/v1/jobs", headers=_auth(token))
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"

    weak = await client.post(
        f"{AUTH}/change-password",
        headers=_auth(token),
        json={"current_password": temporary, "new_password": "short"},
    )
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "weak_password"

    wrong = await client.post(
        f"{AUTH}/change-password",
        headers=_auth(token),
        json={"current_password": "not-it", "new_password": NEW_PASSWORD},
    )
    assert wrong.status_code == 400

    changed = await client.post(
        f"{AUTH}/change-password",
        headers=_auth(token),
        json={"current_password": temporary, "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200
    assert changed.json()["user"]["must_change_password"] is False
    fresh = changed.json()["access_token"]
    assert (await client.get("/api/v1/jobs", headers=_auth(fresh))).status_code == 200


async def test_password_change_signs_out_other_sessions(client: AsyncClient) -> None:
    await login(client, "recruiter")
    old_cookie = client.cookies["refresh_token"]
    token = await login(client, "recruiter")

    changed = await client.post(
        f"{AUTH}/change-password",
        headers=_auth(token),
        json={"current_password": DEMO_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200

    client.cookies.clear()
    stale = await client.post(f"{AUTH}/refresh", headers={"Cookie": f"refresh_token={old_cookie}"})
    assert stale.status_code == 401


async def test_admin_resets_and_deactivates_users(client: AsyncClient) -> None:
    admin = await login(client, "hradmin")
    created = await _create(client, admin)
    user_id = created["user"]["id"]

    reset = await client.post(f"{USERS}/{user_id}/reset-password", headers=_auth(admin))
    assert reset.status_code == 200
    assert reset.json()["temporary_password"] != created["temporary_password"]

    deactivated = await client.patch(
        f"{USERS}/{user_id}", headers=_auth(admin), json={"is_active": False}
    )
    assert deactivated.json()["is_active"] is False
    login_attempt = await client.post(
        f"{AUTH}/login",
        json={"email": "temp.user@example.com", "password": reset.json()["temporary_password"]},
    )
    assert login_attempt.status_code == 401

    duplicate = await client.post(
        USERS,
        headers=_auth(admin),
        json={"email": "temp.user@example.com", "full_name": "Again", "role": "recruiter"},
    )
    assert duplicate.status_code == 409


async def test_admin_guards(client: AsyncClient) -> None:
    hr_admin = await login(client, "hradmin")
    users = (await client.get(USERS, headers=_auth(hr_admin))).json()["items"]
    by_role = {u["role"]: u for u in users}
    me = by_role["hr_admin"]["id"]

    self_demote = await client.patch(
        f"{USERS}/{me}", headers=_auth(hr_admin), json={"role": "recruiter"}
    )
    assert self_demote.status_code == 403

    touch_super = await client.post(
        f"{USERS}/{by_role['super_admin']['id']}/reset-password", headers=_auth(hr_admin)
    )
    assert touch_super.status_code == 403

    super_admin = await login(client, "superadmin")
    last_hr_admin = await client.patch(
        f"{USERS}/{me}", headers=_auth(super_admin), json={"is_active": False}
    )
    assert last_hr_admin.status_code == 409
    assert last_hr_admin.json()["error"]["code"] == "last_admin"


async def test_reset_link_points_at_the_portal(
    client: AsyncClient, sent_emails: list[dict[str, Any]]
) -> None:
    await client.post(f"{AUTH}/forgot-password", json={"email": f"recruiter@{DEMO_EMAIL_DOMAIN}"})

    assert len(sent_emails) == 1
    assert "/reset-password?token=" in sent_emails[0]["body"]
