import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.reference_data import DEFAULT_DEPARTMENTS
from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_public_config_has_branding_and_flags_only(client: AsyncClient) -> None:
    response = await client.get("/api/v1/config")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"org_name", "logo_data_url", "features"}
    assert set(body["features"]) == {
        "public_careers",
        "interviews",
        "offers",
        "requisitions",
        "audit_ui",
    }


async def test_admin_renames_org_and_sets_logo(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    renamed = await client.patch(
        "/api/v1/org/settings", headers=_auth(token), json={"name": "Pixel Works"}
    )
    assert renamed.status_code == 200
    assert (await client.get("/api/v1/config")).json()["org_name"] == "Pixel Works"

    logo = await client.put(
        "/api/v1/org/logo", headers=_auth(token), files={"file": ("logo.png", PNG, "image/png")}
    )
    assert logo.status_code == 200
    assert logo.json()["logo_data_url"].startswith("data:image/png;base64,")

    not_image = await client.put(
        "/api/v1/org/logo",
        headers=_auth(token),
        files={"file": ("logo.png", b"<svg onload=alert(1)>", "image/png")},
    )
    assert not_image.status_code == 422

    applications = await client.get("/api/v1/applications", headers=_auth(token))
    first = applications.json()["items"][0]
    sent = await client.post(
        "/api/v1/emails/send",
        headers=_auth(token),
        json={
            "candidate_id": first["candidate_id"],
            "subject": "Update from {{org_name}}",
            "body": "Best regards,\n{{org_name}} HR",
        },
    )
    assert sent.status_code == 200
    assert sent.json()["subject"] == "Update from Pixel Works"
    assert sent.json()["body"].endswith("Pixel Works HR")

    recruiter = await login(client, "recruiter")
    denied = await client.patch(
        "/api/v1/org/settings", headers=_auth(recruiter), json={"name": "Nope"}
    )
    assert denied.status_code == 403


async def test_reference_departments_and_admin_management(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    listed = await client.get("/api/v1/departments", headers=_auth(token))
    names = {d["name"] for d in listed.json()}
    assert set(DEFAULT_DEPARTMENTS) <= names

    created = await client.post("/api/v1/departments", headers=_auth(token), json={"name": "SEO"})
    assert created.status_code == 201
    department_id = created.json()["id"]
    duplicate = await client.post("/api/v1/departments", headers=_auth(token), json={"name": "seo"})
    assert duplicate.status_code == 409

    renamed = await client.patch(
        f"/api/v1/departments/{department_id}",
        headers=_auth(token),
        json={"name": "SEO & Content", "is_active": False},
    )
    assert renamed.json()["name"] == "SEO & Content"
    assert renamed.json()["is_active"] is False

    active = await client.get("/api/v1/departments", headers=_auth(token))
    assert "SEO & Content" not in {d["name"] for d in active.json()}
    everything = await client.get(
        "/api/v1/departments", headers=_auth(token), params={"include_inactive": True}
    )
    assert "SEO & Content" in {d["name"] for d in everything.json()}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/public/jobs"),
        ("POST", "/api/v1/public/jobs"),
        ("GET", "/api/v1/interviews"),
        ("GET", "/api/v1/interviews/mine"),
        ("POST", "/api/v1/interviews"),
        ("PUT", "/api/v1/interviews/abc"),
        ("DELETE", "/api/v1/interviews/abc"),
        ("GET", "/api/v1/offers"),
        ("POST", "/api/v1/offers"),
        ("PATCH", "/api/v1/offers/abc"),
        ("GET", "/api/v1/requisitions"),
        ("POST", "/api/v1/requisitions"),
        ("GET", "/api/v1/audit-logs"),
        ("POST", "/api/v1/audit-logs"),
    ],
)
async def test_disabled_modules_answer_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    settings = get_settings()
    for flag in ("public_careers", "interviews", "offers", "requisitions", "audit_ui"):
        monkeypatch.setattr(settings, f"enable_{flag}", False)
    token = await login(client, "superadmin")

    response = await client.request(method, path, headers=_auth(token), json={})

    assert response.status_code == 404, response.text


def test_flags_default_to_off() -> None:
    fields = type(get_settings()).model_fields
    for flag in ("public_careers", "interviews", "offers", "requisitions", "audit_ui"):
        assert fields[f"enable_{flag}"].default is False
