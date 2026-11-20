from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")

JOBS = "/api/v1/jobs"
PUBLIC = "/api/v1/public/jobs"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _job_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "title": "Data Engineer",
        "work_mode": "remote",
        "employment_type": "full_time",
        "description": "Build our data platform.",
        "requirements": {
            "required_skills": [{"name": "Python", "weight": 1}, {"name": "SQL", "weight": 0.8}],
            "preferred_skills": [{"name": "Airflow", "weight": 0.5}],
            "min_experience": 3,
            "max_experience": 8,
            "education_level": "Bachelor's",
        },
        **overrides,
    }


async def test_create_publish_and_view_on_careers_site(client: AsyncClient) -> None:
    token = await login(client, "recruiter")

    created = await client.post(JOBS, headers=_auth(token), json=_job_payload())
    assert created.status_code == 201
    job = created.json()
    assert job["slug"] == "data-engineer"
    assert job["status"] == "draft"
    assert job["requirements"]["required_skills"][0] == {"name": "Python", "weight": 1.0}
    assert any(m["team_role"] == "recruiter" for m in job["team"])

    assert (await client.get(f"{PUBLIC}/{job['slug']}")).status_code == 404

    published = await client.post(f"{JOBS}/{job['id']}/publish", headers=_auth(token))
    assert published.status_code == 200
    assert published.json()["status"] == "open"

    public = await client.get(f"{PUBLIC}/{job['slug']}")
    assert public.status_code == 200
    assert public.json()["required_skills"] == ["Python", "SQL"]
    assert "team" not in public.json()

    listing = await client.get(PUBLIC, params={"q": "data"})
    assert [j["slug"] for j in listing.json()["items"]] == ["data-engineer"]

    closed = await client.post(f"{JOBS}/{job['id']}/close", headers=_auth(token))
    assert closed.json()["status"] == "closed"
    assert (await client.get(f"{PUBLIC}/{job['slug']}")).status_code == 404


async def test_duplicate_titles_get_unique_slugs(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    first = await client.post(JOBS, headers=_auth(token), json=_job_payload(title="QA Lead"))
    second = await client.post(JOBS, headers=_auth(token), json=_job_payload(title="QA Lead"))

    assert first.json()["slug"] == "qa-lead"
    assert second.json()["slug"] == "qa-lead-2"


async def test_list_filters_sorts_and_paginates(client: AsyncClient) -> None:
    token = await login(client, "recruiter")

    response = await client.get(
        JOBS, headers=_auth(token), params={"status": "open", "sort": "title", "page_size": 1}
    )

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 2
    assert [j["title"] for j in body["items"]] == ["Frontend Engineer"]

    bad_sort = await client.get(JOBS, headers=_auth(token), params={"sort": "password"})
    assert bad_sort.status_code == 400


async def test_hiring_manager_reads_own_jobs_but_cannot_edit(client: AsyncClient) -> None:
    token = await login(client, "manager")

    listing = await client.get(JOBS, headers=_auth(token))
    assert {j["slug"] for j in listing.json()["items"]} == {
        "senior-backend-engineer",
        "frontend-engineer",
    }

    assert (await client.post(JOBS, headers=_auth(token), json=_job_payload())).status_code == 403
    job_id = listing.json()["items"][0]["id"]
    patch = await client.patch(f"{JOBS}/{job_id}", headers=_auth(token), json={"title": "Changed"})
    assert patch.status_code == 403


async def test_publish_requires_a_description(client: AsyncClient) -> None:
    token = await login(client, "recruiter")
    job = (await client.post(JOBS, headers=_auth(token), json=_job_payload(description=""))).json()

    response = await client.post(f"{JOBS}/{job['id']}/publish", headers=_auth(token))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "job_incomplete"
