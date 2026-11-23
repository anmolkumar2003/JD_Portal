import io
import re
import zipfile
from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Application, Candidate, Document, ParsedProfile, PipelineStage
from app.models.enums import ParseStatus, StageType
from tests.conftest import login

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
ANDROID = "senior-android-developer"
SHOPIFY = "shopify-developer"


def _docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


def _form(email: str = "asha@example.com", **overrides: str) -> dict[str, str]:
    return {
        "first_name": "Asha",
        "last_name": "Rao",
        "email": email,
        "phone": "+91 98765 43210",
        "current_company": "Globex",
        "total_experience_years": "4.5",
        "notice_period_days": "30",
        "linkedin_url": "https://linkedin.com/in/asha",
        "cover_letter": "",
        "consent": "true",
        "website": "",
        **overrides,
    }


async def _apply(
    client: AsyncClient,
    slug: str = ANDROID,
    *,
    data: dict[str, str] | None = None,
    file: tuple[str, bytes, str] = ("Asha CV.pdf", PDF, "application/pdf"),
) -> Any:
    return await client.post(
        f"/api/v1/public/jobs/{slug}/apply", data=data or _form(), files={"cv": file}
    )


async def test_apply_creates_candidate_application_document_and_email(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    sent_emails: list[dict[str, Any]],
    stored_objects: dict[str, bytes],
) -> None:
    response = await _apply(client)
    assert response.status_code == 201, response.text
    reference = response.json()["reference_no"]
    assert re.fullmatch(r"APP-\d{4}-\d{6}", reference)

    async with db() as session:
        application = await session.scalar(
            select(Application).where(Application.reference_no == reference)
        )
        assert application is not None
        stage = await session.get(PipelineStage, application.stage_id)
        assert stage is not None and stage.type == StageType.APPLIED
        candidate = await session.get(Candidate, application.candidate_id)
        assert candidate is not None
        assert candidate.consent_given_at is not None and candidate.consent_version
        document = await session.scalar(
            select(Document).where(Document.application_id == application.id)
        )
        assert document is not None and document.mime_type == "application/pdf"
        assert document.file_name == "Asha CV.pdf"
        profile = await session.scalar(
            select(ParsedProfile).where(ParsedProfile.document_id == document.id)
        )
        assert profile is not None and profile.parse_status == ParseStatus.PENDING

    assert stored_objects[document.storage_key] == PDF
    assert sent_emails[0]["to"] == "asha@example.com"
    assert reference in sent_emails[0]["subject"]


async def test_repeat_applicant_reuses_candidate_and_duplicate_is_rejected(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    sent_emails: list[dict[str, Any]],
    stored_objects: dict[str, bytes],
) -> None:
    assert (await _apply(client, ANDROID)).status_code == 201
    docx = ("cv.docx", _docx(), "application/octet-stream")
    second = await _apply(client, SHOPIFY, data=_form("ASHA@example.com"), file=docx)
    assert second.status_code == 201, second.text

    duplicate = await _apply(client, ANDROID)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "already_applied"

    async with db() as session:
        candidates = await session.scalar(
            select(func.count()).select_from(Candidate).where(Candidate.email == "asha@example.com")
        )
        candidate = await session.scalar(
            select(Candidate).where(Candidate.email == "asha@example.com")
        )
        assert candidate is not None
        applications = await session.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.candidate_id == candidate.id)
        )
    assert candidates == 1
    assert applications == 2
    assert len(stored_objects) == 2


async def test_rejects_fake_cv_missing_consent_and_honeypot(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    sent_emails: list[dict[str, Any]],
    stored_objects: dict[str, bytes],
) -> None:
    fake = await _apply(client, file=("cv.pdf", b"MZ not really a pdf", "application/pdf"))
    assert fake.status_code == 422
    assert fake.json()["error"]["code"] == "invalid_file"

    no_consent = await _apply(client, data=_form(consent="false"))
    assert no_consent.status_code == 422

    bot = await _apply(client, data=_form(website="http://spam.example"))
    assert bot.status_code == 400
    assert stored_objects == {}
    assert sent_emails == []


async def test_sixth_application_from_same_ip_is_rate_limited(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    sent_emails: list[dict[str, Any]],
    stored_objects: dict[str, bytes],
) -> None:
    for i in range(5):
        response = await _apply(client, data=_form(f"person{i}@example.com"))
        assert response.status_code == 201, response.text
    limited = await _apply(client, data=_form("person6@example.com"))
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"


async def test_download_url_is_signed_and_scoped(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    sent_emails: list[dict[str, Any]],
    stored_objects: dict[str, bytes],
) -> None:
    created = await _apply(client, SHOPIFY, data=_form("download-scope@example.com"))
    assert created.status_code == 201, created.text
    reference = created.json()["reference_no"]
    async with db() as session:
        application = await session.scalar(
            select(Application).where(Application.reference_no == reference)
        )
        assert application is not None
        document = await session.scalar(
            select(Document).where(Document.application_id == application.id)
        )
        assert document is not None
        document_id = document.id
        storage_key = document.storage_key

    assert stored_objects[storage_key] == PDF

    recruiter = await login(client, "recruiter")
    ok = await client.get(
        f"/api/v1/documents/{document_id}/download-url",
        headers={"Authorization": f"Bearer {recruiter}"},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    # Default: same-origin API proxy with a short-lived download JWT (MinIO stays private).
    assert body["url"].startswith(f"/api/v1/documents/{document_id}/content?token=")
    assert body["expires_in"] == 300

    content = await client.get(body["url"])
    assert content.status_code == 200, content.text
    assert content.content == PDF

    # The interviewer is not on the Shopify job's team.
    interviewer = await login(client, "interviewer")
    hidden = await client.get(
        f"/api/v1/documents/{document_id}/download-url",
        headers={"Authorization": f"Bearer {interviewer}"},
    )
    assert hidden.status_code == 404

    anonymous = await client.get(f"/api/v1/documents/{document_id}/download-url")
    assert anonymous.status_code == 401
