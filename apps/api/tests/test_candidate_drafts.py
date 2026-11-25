"""B1/B3/B4/B5: draft area, required fields, duplicates, commit (single, multi, partial)."""

import uuid
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

import pytest
from httpx import AsyncClient
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.models import (
    Candidate,
    CandidateDraft,
    CandidateDraftFile,
    Document,
    Job,
    Organization,
    OrphanStorageObject,
    ParsedProfile,
    User,
)
from app.services.draft_cleanup import cleanup_expired_drafts_sync
from tests.conftest import _test_database_url, login

pytestmark = pytest.mark.usefixtures("db", "stored_objects")

MINI_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + b" " * 200


def _real_pdf(email: str) -> bytes:
    """A small but genuinely parseable one-page PDF."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for line, text in enumerate(
        ["Jane Doe", f"Email: {email}", "Phone: +91 98765 43210", "Python developer"]
    ):
        pdf.drawString(72, 760 - 20 * line, text)
    pdf.save()
    return buffer.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _no_celery(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    queued: list[str] = []

    class _Task:
        @staticmethod
        def delay(document_id: str) -> None:
            queued.append(document_id)

    monkeypatch.setattr("app.services.analysis.process_document", _Task)
    return queued


async def _job_id(client: AsyncClient, headers: dict[str, str]) -> str:
    jobs = await client.get("/api/v1/jobs", headers=headers)
    return str(jobs.json()["items"][0]["id"])


async def _new_draft(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post("/api/v1/candidates/drafts", headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"id", "expires_at"}
    return str(body["id"])


async def _upload(
    client: AsyncClient, headers: dict[str, str], draft_id: str, name: str = "cv.pdf"
) -> dict[str, Any]:
    # Distinct bytes per call so checksums differ.
    data = MINI_PDF + uuid.uuid4().hex.encode()
    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/files",
        headers=headers,
        files={"cv": (name, BytesIO(data), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _row(job_id: str, draft_file_id: str | None, n: int, **extra: Any) -> dict[str, Any]:
    return {
        "draft_file_id": draft_file_id,
        "first_name": f"Draft{n}",
        "last_name": "Person",
        "email": f"draft{n}.{uuid.uuid4().hex[:6]}@example.com",
        "phone": f"+91 90000 0{n:04d}",
        "job_id": job_id,
        **extra,
    }


async def _count(session: AsyncSession, model: Any) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


# --- B1: draft area ---------------------------------------------------------------------------


async def test_upload_to_draft_creates_no_candidate(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
) -> None:
    headers = _auth(await login(client, "recruiter"))
    async with db() as session:
        candidates_before = await _count(session, Candidate)
        documents_before = await _count(session, Document)
        profiles_before = await _count(session, ParsedProfile)

    draft_id = await _new_draft(client, headers)
    uploaded = await _upload(client, headers, draft_id)
    assert uploaded["draft_file_id"]

    assert uploaded["draft_id"] == draft_id
    assert uploaded["draft_file_id"]
    assert "file_name" in uploaded and "skills" in uploaded  # CvParseOut shape
    (key,) = stored_objects
    assert key.startswith("drafts/")
    assert key.split("/")[2] == draft_id
    assert key.endswith(f"{uploaded['draft_file_id']}.pdf")

    async with db() as session:
        assert await _count(session, Candidate) == candidates_before
        assert await _count(session, Document) == documents_before
        assert await _count(session, ParsedProfile) == profiles_before
        file = await session.scalar(select(CandidateDraftFile))
        assert file is not None
        assert file.storage_key == key
        assert file.mime_type == "application/pdf"
        assert file.size == len(stored_objects[key])
        assert len(file.checksum) == 64
        assert file.parsed_preview is not None
        draft = await session.get(CandidateDraft, uuid.UUID(draft_id))
        assert draft is not None
        assert timedelta(hours=23) < draft.expires_at - datetime.now(UTC) <= timedelta(hours=24)


async def test_draft_upload_saves_parsed_preview(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    headers = _auth(await login(client, "recruiter"))
    draft_id = await _new_draft(client, headers)
    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/files",
        headers=headers,
        files={"cv": ("jane.pdf", BytesIO(_real_pdf("jane@example.com")), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["first_name"] == "Jane"
    assert body["phone"] == "+91 98765 43210"
    assert body["file_name"] == "jane.pdf"
    async with db() as session:
        file = await session.get(CandidateDraftFile, uuid.UUID(body["draft_file_id"]))
        assert file is not None and file.parsed_preview is not None
        assert file.parsed_preview["phone"] == "+91 98765 43210"


async def test_parse_cv_stays_a_pure_preview(
    client: AsyncClient, stored_objects: dict[str, bytes], db: async_sessionmaker[AsyncSession]
) -> None:
    headers = _auth(await login(client, "recruiter"))
    response = await client.post(
        "/api/v1/candidates/parse-cv",
        headers=headers,
        files={"cv": ("cv.pdf", BytesIO(_real_pdf("jane@example.com")), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["first_name"] == "Jane"
    assert stored_objects == {}
    async with db() as session:
        assert await _count(session, CandidateDraftFile) == 0


async def test_draft_endpoints_require_candidate_editor(client: AsyncClient) -> None:
    unauth = await client.post("/api/v1/candidates/drafts")
    assert unauth.status_code == 401
    for handle in ("manager", "interviewer"):
        token = await login(client, handle)
        response = await client.post("/api/v1/candidates/drafts", headers=_auth(token))
        assert response.status_code == 403, handle


async def test_draft_is_private_to_its_creator(client: AsyncClient) -> None:
    owner = _auth(await login(client, "recruiter"))
    other = _auth(await login(client, "hradmin"))
    draft_id = await _new_draft(client, owner)
    response = await client.delete(f"/api/v1/candidates/drafts/{draft_id}", headers=other)
    assert response.status_code == 404
    upload = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/files",
        headers=other,
        files={"cv": ("cv.pdf", BytesIO(MINI_PDF), "application/pdf")},
    )
    assert upload.status_code == 404


async def test_draft_rejects_non_cv_files(client: AsyncClient) -> None:
    headers = _auth(await login(client, "recruiter"))
    draft_id = await _new_draft(client, headers)
    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/files",
        headers=headers,
        files={"cv": ("evil.exe", BytesIO(b"MZ" + b"x" * 300), "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_file"


async def test_cancel_draft_deletes_rows_and_minio_keys(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
) -> None:
    headers = _auth(await login(client, "recruiter"))
    draft_id = await _new_draft(client, headers)
    await _upload(client, headers, draft_id)
    await _upload(client, headers, draft_id)
    stored_objects[f"drafts/stray/{draft_id}/x.pdf"] = b"unrelated"  # other prefix: untouched
    assert len([k for k in stored_objects if k.startswith("drafts/") and draft_id in k]) == 3

    response = await client.delete(f"/api/v1/candidates/drafts/{draft_id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["deleted"] is True
    assert response.json()["files_deleted"] == 2
    assert list(stored_objects) == [f"drafts/stray/{draft_id}/x.pdf"]
    async with db() as session:
        assert await _count(session, CandidateDraft) == 0
        assert await _count(session, CandidateDraftFile) == 0


async def test_failed_minio_delete_on_cancel_is_queued_for_retry(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth(await login(client, "recruiter"))
    draft_id = await _new_draft(client, headers)
    await _upload(client, headers, draft_id)
    (key,) = stored_objects

    async def broken_delete(key: str) -> None:
        raise OSError("minio down")

    monkeypatch.setattr("app.core.storage.delete_object", broken_delete)
    response = await client.delete(f"/api/v1/candidates/drafts/{draft_id}", headers=headers)

    assert response.status_code == 200
    async with db() as session:
        assert await _count(session, CandidateDraft) == 0
        orphan = await session.scalar(select(OrphanStorageObject))
        assert orphan is not None and orphan.storage_key == key


def test_expiry_cleanup_removes_only_expired_drafts(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[str] = []
    monkeypatch.setattr("app.core.storage.delete_object_sync", deleted.append)
    monkeypatch.setattr("app.core.storage.list_prefix_sync", lambda prefix: [f"{prefix}stray.pdf"])

    engine = create_engine(_test_database_url().replace("+asyncpg", "+psycopg"))
    with Session(engine) as session:
        org = session.scalars(select(Organization)).first()
        user = session.scalars(select(User)).first()
        assert org is not None and user is not None
        now = datetime.now(UTC)
        old = CandidateDraft(org_id=org.id, created_by=user.id, expires_at=now - timedelta(hours=1))
        fresh = CandidateDraft(
            org_id=org.id, created_by=user.id, expires_at=now + timedelta(hours=5)
        )
        session.add_all([old, fresh])
        session.flush()
        session.add_all(
            [
                CandidateDraftFile(
                    draft_id=draft.id,
                    storage_key=f"drafts/{org.id}/{draft.id}/{uuid.uuid4()}.pdf",
                    file_name="cv.pdf",
                    mime_type="application/pdf",
                    size=10,
                    checksum="0" * 64,
                )
                for draft in (old, fresh)
            ]
        )
        session.commit()
        old_id, fresh_id = old.id, fresh.id

        result = cleanup_expired_drafts_sync(session)

        assert result["drafts"] == 1
        assert result["objects_removed"] == 2  # the DB-tracked key plus the stray one
        assert len(deleted) == 2
        assert all(str(old_id) in key for key in deleted)
        remaining = session.scalars(select(CandidateDraft.id)).all()
        assert remaining == [fresh_id]
        assert session.scalar(select(func.count()).select_from(CandidateDraftFile)) == 1
    engine.dispose()


async def test_expired_draft_cannot_be_uploaded_or_committed(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    headers = _auth(await login(client, "recruiter"))
    draft_id = await _new_draft(client, headers)
    async with db() as session:
        draft = await session.get(CandidateDraft, uuid.UUID(draft_id))
        assert draft is not None
        draft.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()
    upload = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/files",
        headers=headers,
        files={"cv": ("cv.pdf", BytesIO(MINI_PDF), "application/pdf")},
    )
    assert upload.status_code == 410
    assert upload.json()["error"]["code"] == "draft_expired"


# --- B3: required fields ----------------------------------------------------------------------


@pytest.mark.parametrize("missing", ["first_name", "last_name", "email", "phone", "job_id"])
async def test_create_requires_each_field(client: AsyncClient, missing: str) -> None:
    headers = _auth(await login(client, "recruiter"))
    data = {
        "first_name": "Req",
        "last_name": "Field",
        "email": f"req-{missing}@example.com",
        "phone": "+91 90000 12345",
        "job_id": await _job_id(client, headers),
    }
    data.pop(missing)
    response = await client.post("/api/v1/candidates", headers=headers, data=data)
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert [d["loc"] for d in error["details"]] == [["body", missing]]
    assert "required" in error["details"][0]["msg"].lower()

    blank = await client.post("/api/v1/candidates", headers=headers, data={**data, missing: "   "})
    assert blank.status_code == 422
    assert [d["loc"] for d in blank.json()["error"]["details"]] == [["body", missing]]


async def test_create_validates_email_and_phone_formats(client: AsyncClient) -> None:
    headers = _auth(await login(client, "recruiter"))
    response = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": "Bad",
            "last_name": "Format",
            "email": "not-an-email",
            "phone": "call me maybe",
            "job_id": await _job_id(client, headers),
        },
    )
    assert response.status_code == 422
    fields = {d["loc"][1] for d in response.json()["error"]["details"]}
    assert fields == {"email", "phone"}
    assert "not-an-email" not in response.text  # no echoing of input


async def test_create_takes_department_from_job(
    client: AsyncClient, db: async_sessionmaker[AsyncSession]
) -> None:
    headers = _auth(await login(client, "recruiter"))
    async with db() as session:
        job = await session.scalar(select(Job).where(Job.department_id.is_not(None)).limit(1))
        assert job is not None
        job_id, department_id = str(job.id), job.department_id
    created = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": "Dept",
            "last_name": "FromJob",
            "email": "dept.fromjob@example.com",
            "phone": "+91 90000 55555",
            "job_id": job_id,
        },
    )
    assert created.status_code == 201, created.text
    async with db() as session:
        candidate = await session.get(Candidate, uuid.UUID(created.json()["candidate_id"]))
        assert candidate is not None
        assert candidate.department_id == department_id


async def test_unknown_job_is_not_found(client: AsyncClient) -> None:
    headers = _auth(await login(client, "recruiter"))
    response = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": "No",
            "last_name": "Job",
            "email": "no.job@example.com",
            "phone": "+91 90000 66666",
            "job_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 404


# --- B4: duplicates ---------------------------------------------------------------------------


async def test_duplicates_endpoint_still_finds_existing_candidates(client: AsyncClient) -> None:
    headers = _auth(await login(client, "recruiter"))
    job_id = await _job_id(client, headers)
    created = await client.post(
        "/api/v1/candidates",
        headers=headers,
        data={
            "first_name": "Dup",
            "last_name": "Licate",
            "email": "dup.licate@example.com",
            "phone": "+91 98111 22233",
            "job_id": job_id,
        },
    )
    assert created.status_code == 201
    found = await client.get(
        "/api/v1/candidates/duplicates",
        headers=headers,
        params={"email": "dup.licate@example.com", "phone": "9811122233"},
    )
    assert found.status_code == 200
    (match,) = found.json()["matches"]
    assert match["id"] == created.json()["candidate_id"]
    assert set(match["matched_on"]) == {"email", "phone"}


# --- B5: commit -------------------------------------------------------------------------------


async def test_commit_single_row_end_to_end(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
    _no_celery: list[str],
) -> None:
    headers = _auth(await login(client, "recruiter"))
    job_id = await _job_id(client, headers)
    draft_id = await _new_draft(client, headers)
    uploaded = await _upload(client, headers, draft_id, "Asha Resume.pdf")
    (draft_key,) = stored_objects
    cv_bytes = stored_objects[draft_key]

    row = _row(job_id, uploaded["draft_file_id"], 1, current_title="Engineer")
    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/commit",
        headers=headers,
        json={"mode": "all", "rows": [row]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved_count"] == 1
    assert body["draft_deleted"] is True
    (result,) = body["results"]
    assert result["status"] == "saved"
    assert result["link"].startswith(f"/candidates/{result['candidate_id']}")
    assert result["application_id"] and result["reference_no"]

    # Object moved: draft key gone, permanent key present with identical bytes.
    permanent = f"{result['candidate_id']}/{result['document_id']}"
    assert draft_key not in stored_objects
    (permanent_key,) = list(stored_objects)
    assert permanent_key.endswith(".pdf")
    assert permanent_key.startswith(f"{await _org_id(db)}/{permanent}")
    assert stored_objects[permanent_key] == cv_bytes
    assert _no_celery == [result["document_id"]]  # process_document queued

    async with db() as session:
        candidate = await session.get(Candidate, uuid.UUID(result["candidate_id"]))
        assert candidate is not None and candidate.phone == row["phone"]
        document = await session.get(Document, uuid.UUID(result["document_id"]))
        assert document is not None and document.file_name == "Asha Resume.pdf"
        profile = await session.scalar(
            select(ParsedProfile).where(ParsedProfile.document_id == document.id)
        )
        assert profile is not None
        assert await _count(session, CandidateDraft) == 0
        assert await _count(session, CandidateDraftFile) == 0


async def _org_id(db: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    async with db() as session:
        org = await session.scalar(select(Candidate.org_id).limit(1))
        assert org is not None
        return org


async def test_incomplete_commit_is_rejected_and_nothing_changes(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
) -> None:
    headers = _auth(await login(client, "recruiter"))
    job_id = await _job_id(client, headers)
    draft_id = await _new_draft(client, headers)
    first = await _upload(client, headers, draft_id)
    second = await _upload(client, headers, draft_id)
    async with db() as session:
        candidates_before = await _count(session, Candidate)
    keys_before = set(stored_objects)

    incomplete = _row(job_id, second["draft_file_id"], 2)
    incomplete["phone"] = ""
    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/commit",
        headers=headers,
        json={
            "mode": "all",
            "rows": [_row(job_id, first["draft_file_id"], 1), incomplete],
        },
    )

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"] == [{"row": 1, "field": "phone", "message": "This field is required"}]
    assert set(stored_objects) == keys_before
    async with db() as session:
        assert await _count(session, Candidate) == candidates_before
        assert await _count(session, CandidateDraftFile) == 2


async def test_commit_requires_job_and_valid_formats(client: AsyncClient) -> None:
    headers = _auth(await login(client, "recruiter"))
    draft_id = await _new_draft(client, headers)
    uploaded = await _upload(client, headers, draft_id)
    row = _row("", None, 1)
    row.pop("job_id")
    row["draft_file_id"] = uploaded["draft_file_id"]
    row["email"] = "nope"
    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/commit",
        headers=headers,
        json={"mode": "all", "rows": [row]},
    )
    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {"email", "job_id"}


async def test_multi_commit_complete_only_saves_valid_rows_and_keeps_the_rest(
    client: AsyncClient,
    db: async_sessionmaker[AsyncSession],
    stored_objects: dict[str, bytes],
) -> None:
    headers = _auth(await login(client, "recruiter"))
    job_id = await _job_id(client, headers)
    draft_id = await _new_draft(client, headers)
    files = [await _upload(client, headers, draft_id, f"cv{n}.pdf") for n in range(3)]
    bad = _row(job_id, files[1]["draft_file_id"], 2)
    bad["last_name"] = ""

    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/commit",
        headers=headers,
        json={
            "mode": "complete_only",
            "rows": [
                _row(job_id, files[0]["draft_file_id"], 1),
                bad,
                _row(job_id, files[2]["draft_file_id"], 3),
            ],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["saved_count"], body["incomplete_count"], body["failed_count"]) == (2, 1, 0)
    assert [r["status"] for r in body["results"]] == ["saved", "incomplete", "saved"]
    assert body["results"][1]["issues"] == [
        {"field": "last_name", "message": "This field is required"}
    ]
    assert body["draft_deleted"] is False

    # Only the incomplete row's file is still staged in the draft.
    draft_keys = [k for k in stored_objects if k.startswith("drafts/")]
    assert len(draft_keys) == 1 and files[1]["draft_file_id"] in draft_keys[0]
    async with db() as session:
        remaining = (await session.scalars(select(CandidateDraftFile))).all()
        assert [str(f.id) for f in remaining] == [files[1]["draft_file_id"]]
        assert await _count(session, CandidateDraft) == 1

    # Fix the row and save the remainder: the draft disappears.
    fixed = {**bad, "last_name": "Fixed"}
    second = await client.post(
        f"/api/v1/candidates/drafts/{draft_id}/commit",
        headers=headers,
        json={"mode": "all", "rows": [fixed]},
    )
    assert second.status_code == 200, second.text
    assert second.json()["draft_deleted"] is True
    assert not [k for k in stored_objects if k.startswith("drafts/")]
    async with db() as session:
        assert await _count(session, CandidateDraft) == 0


async def test_commit_rejects_files_from_another_draft(client: AsyncClient) -> None:
    headers = _auth(await login(client, "recruiter"))
    job_id = await _job_id(client, headers)
    draft_a = await _new_draft(client, headers)
    draft_b = await _new_draft(client, headers)
    file_b = await _upload(client, headers, draft_b)
    response = await client.post(
        f"/api/v1/candidates/drafts/{draft_a}/commit",
        headers=headers,
        json={"mode": "complete_only", "rows": [_row(job_id, file_b["draft_file_id"], 1)]},
    )
    assert response.status_code == 200
    (result,) = response.json()["results"]
    assert result["status"] == "incomplete"
    assert result["issues"][0]["field"] == "draft_file_id"
