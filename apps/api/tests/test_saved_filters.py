import pytest
from httpx import AsyncClient

from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_saved_filters_crud(client: AsyncClient) -> None:
    token = await login(client, "recruiter")
    headers = _auth(token)

    created = await client.post(
        "/api/v1/saved-filters",
        headers=headers,
        json={"name": "High scorers", "filters": {"score_min": "70", "source": "linkedin"}},
    )
    assert created.status_code == 201, created.text
    filter_id = created.json()["id"]

    listed = await client.get("/api/v1/saved-filters", headers=headers)
    assert any(f["id"] == filter_id for f in listed.json())

    dup = await client.post(
        "/api/v1/saved-filters",
        headers=headers,
        json={"name": "High scorers", "filters": {}},
    )
    assert dup.status_code == 409

    deleted = await client.delete(f"/api/v1/saved-filters/{filter_id}", headers=headers)
    assert deleted.status_code == 204


async def test_shortlisted_and_tag_filters(client: AsyncClient) -> None:
    token = await login(client, "recruiter")
    headers = _auth(token)
    listed = await client.get(
        "/api/v1/applications",
        headers=headers,
        params={"is_shortlisted": "false", "page_size": 5},
    )
    assert listed.status_code == 200
