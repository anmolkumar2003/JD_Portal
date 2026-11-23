"""Simple interview ratings and advisory final score (Phase 3)."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _first_application(client: AsyncClient, token: str) -> str:
    listed = await client.get("/api/v1/applications", headers=_auth(token))
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items
    app_id = items[0]["id"]
    assert isinstance(app_id, str)
    return app_id


async def test_rating_crud_and_final_score(client: AsyncClient) -> None:
    token = await login(client, "recruiter")
    headers = _auth(token)
    application_id = await _first_application(client, token)

    created = await client.post(
        f"/api/v1/applications/{application_id}/ratings",
        headers=headers,
        json={
            "round_name": "Technical round 1",
            "interviewed_at": datetime.now(UTC).isoformat(),
            "interviewer_name": "Priya Nair",
            "mode": "video",
            "comments": "Solid fundamentals",
            "skill_ratings": [
                {"skill": "Kotlin", "rating": 4},
                {"skill": "Jetpack Compose", "rating": None},
            ],
            "overall_rating": 4,
            "recommendation": "yes",
            "strengths": "Clear communication",
            "concerns": "Limited Compose depth",
        },
    )
    assert created.status_code == 201, created.text
    rating_id = created.json()["id"]
    assert created.json()["overall_rating"] == 4

    listed = await client.get(f"/api/v1/applications/{application_id}/ratings", headers=headers)
    assert listed.status_code == 200
    assert any(r["id"] == rating_id for r in listed.json())

    panel = await client.get(f"/api/v1/applications/{application_id}/final-score", headers=headers)
    assert panel.status_code == 200
    body = panel.json()
    assert body["interview_avg"] == 4.0
    assert body["weights"]["match_weight"] == 50
    assert body["weights"]["interview_weight"] == 50
    assert "Advisory" in body["note"]

    updated = await client.patch(
        f"/api/v1/ratings/{rating_id}",
        headers=headers,
        json={
            "round_name": "Technical round 1",
            "interviewed_at": datetime.now(UTC).isoformat(),
            "interviewer_name": "Priya Nair",
            "mode": "onsite",
            "skill_ratings": [{"skill": "Kotlin", "rating": 5}],
            "overall_rating": 5,
            "recommendation": "strong_yes",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["overall_rating"] == 5

    deleted = await client.delete(f"/api/v1/ratings/{rating_id}", headers=headers)
    assert deleted.status_code == 204


async def test_scoring_weights_admin_only(client: AsyncClient) -> None:
    recruiter = await login(client, "recruiter")
    denied = await client.put(
        "/api/v1/org/scoring-weights",
        headers=_auth(recruiter),
        json={"match_weight": 60, "interview_weight": 40},
    )
    assert denied.status_code == 403

    admin = await login(client, "hradmin")
    bad = await client.put(
        "/api/v1/org/scoring-weights",
        headers=_auth(admin),
        json={"match_weight": 60, "interview_weight": 30},
    )
    assert bad.status_code == 422

    ok = await client.put(
        "/api/v1/org/scoring-weights",
        headers=_auth(admin),
        json={"match_weight": 70, "interview_weight": 30},
    )
    assert ok.status_code == 200
    assert ok.json() == {"match_weight": 70, "interview_weight": 30}

    got = await client.get("/api/v1/org/scoring-weights", headers=_auth(recruiter))
    assert got.json()["match_weight"] == 70
