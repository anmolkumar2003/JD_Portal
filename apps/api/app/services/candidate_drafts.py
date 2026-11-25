"""Add Candidate draft area (B1, B5).

Dropping a CV never creates a candidate, application or permanent document. The file goes to
`drafts/<org>/<draft>/<file>.<ext>` and a `candidate_draft_files` row remembers it with the
parsed preview. Only `commit_draft` turns rows into candidates: it moves each object to its
permanent key (read + put + delete) inside the same flow that creates the Document rows.
Drafts that are cancelled, committed or expired lose their DB rows and storage objects.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import status
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.errors import AppError, field_issues
from app.models import CandidateDraft, CandidateDraftFile, OrphanStorageObject, User
from app.schemas.application import CvParseOut, ManualCandidateCreate
from app.schemas.candidate_drafts import (
    CommitMode,
    DraftCommitIn,
    DraftCommitOut,
    DraftCommitRowIn,
    DraftCommitRowOut,
    DraftDeleteOut,
    DraftFileUploadOut,
    DraftOut,
    RowIssue,
    RowStatus,
)
from app.services.analysis import (
    _load_job_for_create,
    enqueue_cv_processing,
    parse_cv_preview,
    stage_manual_candidate,
)
from app.services.applications import _safe_file_name
from app.services.compliance import write_audit
from app.services.cv_validation import validate_cv
from app.services.draft_cleanup import draft_file_key, draft_prefix

logger = logging.getLogger(__name__)

MAX_DRAFT_FILES = 25


def _not_found(entity: str = "Draft") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", f"{entity} not found")


async def _get_draft(
    session: AsyncSession, user: User, draft_id: uuid.UUID, *, allow_expired: bool = False
) -> CandidateDraft:
    """Drafts are private to the user who started them (404 for anyone else, never 403)."""
    draft = await session.get(CandidateDraft, draft_id)
    if draft is None or draft.org_id != user.org_id or draft.created_by != user.id:
        raise _not_found()
    if not allow_expired and draft.expires_at <= datetime.now(UTC):
        raise AppError(
            status.HTTP_410_GONE, "draft_expired", "This draft has expired. Upload the CV again."
        )
    return draft


# --- Storage clean-up -------------------------------------------------------------------------


async def _purge_keys(session: AsyncSession, keys: list[str], reason: str) -> int:
    """Delete objects; keys that fail go to `orphan_storage_objects` for the hourly retry job."""
    failed: list[str] = []
    for key in dict.fromkeys(keys):
        try:
            await storage.delete_object(key)
        except Exception:
            logger.warning("draft_storage_delete_failed", exc_info=True)
            failed.append(key)
    if failed:
        try:
            await session.execute(
                pg_insert(OrphanStorageObject)
                .values([{"storage_key": key, "reason": reason, "attempts": 1} for key in failed])
                .on_conflict_do_nothing(index_elements=["storage_key"])
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("draft_orphan_record_failed")
    return len(failed)


async def _stray_keys(org_id: uuid.UUID, draft_id: uuid.UUID) -> list[str]:
    """Objects under the draft prefix that no row points to (e.g. a crash between put and
    commit). Best effort: a listing failure must not block the delete."""
    try:
        return await storage.list_prefix(draft_prefix(org_id, draft_id))
    except Exception:
        logger.warning("draft_list_prefix_failed", exc_info=True)
        return []


# --- Create / upload / delete -----------------------------------------------------------------


async def create_draft(session: AsyncSession, user: User) -> DraftOut:
    draft = CandidateDraft(org_id=user.org_id, created_by=user.id)
    session.add(draft)
    await session.flush()
    await write_audit(
        session,
        actor_id=user.id,
        action="candidate_draft.created",
        entity_type="candidate_draft",
        entity_id=draft.id,
    )
    await session.commit()
    return DraftOut(id=draft.id, expires_at=draft.expires_at)


async def upload_draft_file(
    session: AsyncSession,
    user: User,
    draft_id: uuid.UUID,
    data: bytes,
    file_name: str | None,
) -> DraftFileUploadOut:
    """Store one CV in the draft area and parse it. Never creates a Candidate."""
    org_id = user.org_id
    draft = await _get_draft(session, user, draft_id)
    count = int(
        await session.scalar(
            select(func.count())
            .select_from(CandidateDraftFile)
            .where(CandidateDraftFile.draft_id == draft.id)
        )
        or 0
    )
    if count >= MAX_DRAFT_FILES:
        raise AppError(
            status.HTTP_409_CONFLICT,
            "draft_full",
            f"A draft can hold up to {MAX_DRAFT_FILES} CVs.",
        )

    validated = validate_cv(data)
    safe_name = _safe_file_name(file_name, validated.extension)
    try:
        preview = await parse_cv_preview(data, safe_name, validated)
    except AppError:
        raise
    except Exception:
        # The file is fine to keep; HR can type the fields in by hand.
        logger.warning("draft_cv_parse_failed", exc_info=True)
        preview = CvParseOut(file_name=safe_name)

    file_id = uuid.uuid4()
    key = draft_file_key(org_id, draft.id, file_id, validated.extension)
    await storage.put_object(key, data, validated.mime_type)
    session.add(
        CandidateDraftFile(
            id=file_id,
            draft_id=draft.id,
            storage_key=key,
            file_name=safe_name[:255],
            mime_type=validated.mime_type,
            size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            parsed_preview=preview.model_dump(mode="json"),
        )
    )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await _purge_keys(session, [key], "draft_upload_failed")
        raise
    return DraftFileUploadOut(**preview.model_dump(), draft_id=draft_id, draft_file_id=file_id)


async def _delete_draft_rows(
    session: AsyncSession, draft_id: uuid.UUID, *, actor_id: uuid.UUID | None, action: str
) -> list[str]:
    keys = list(
        await session.scalars(
            select(CandidateDraftFile.storage_key).where(CandidateDraftFile.draft_id == draft_id)
        )
    )
    await session.execute(delete(CandidateDraftFile).where(CandidateDraftFile.draft_id == draft_id))
    await session.execute(delete(CandidateDraft).where(CandidateDraft.id == draft_id))
    await write_audit(
        session,
        actor_id=actor_id,
        action=action,
        entity_type="candidate_draft",
        entity_id=draft_id,
        diff={"files": len(keys)},
    )
    await session.commit()
    return keys


async def delete_draft(session: AsyncSession, user: User, draft_id: uuid.UUID) -> DraftDeleteOut:
    """Cancel: remove the draft rows and every object under its prefix."""
    org_id, actor_id = user.org_id, user.id
    draft = await _get_draft(session, user, draft_id, allow_expired=True)
    draft_pk = draft.id
    keys = await _delete_draft_rows(
        session, draft_pk, actor_id=actor_id, action="candidate_draft.deleted"
    )
    keys += await _stray_keys(org_id, draft_pk)
    await _purge_keys(session, keys, "draft_deleted")
    return DraftDeleteOut(id=draft_pk, files_deleted=len(set(keys)))


# --- Commit -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class _FileInfo:
    id: uuid.UUID
    storage_key: str
    file_name: str


@dataclass
class _PreparedRow:
    index: int
    draft_file_id: uuid.UUID | None
    body: ManualCandidateCreate | None
    file: _FileInfo | None
    issues: list[RowIssue]


async def _prepare_rows(
    session: AsyncSession,
    user: User,
    rows: list[DraftCommitRowIn],
    files: dict[uuid.UUID, _FileInfo],
) -> list[_PreparedRow]:
    """Validate every row up front (shape, formats, job access, file ownership)."""
    prepared: list[_PreparedRow] = []
    seen_files: set[uuid.UUID] = set()
    job_ok: dict[uuid.UUID, bool] = {}
    for index, row in enumerate(rows):
        issues: list[RowIssue] = []
        body: ManualCandidateCreate | None = None
        file: _FileInfo | None = None
        if row.draft_file_id is not None:
            file = files.get(row.draft_file_id)
            if file is None:
                issues.append(
                    RowIssue(field="draft_file_id", message="This CV is no longer in the draft")
                )
            elif row.draft_file_id in seen_files:
                issues.append(
                    RowIssue(field="draft_file_id", message="This CV is used by another row")
                )
            seen_files.add(row.draft_file_id)
        try:
            body = ManualCandidateCreate.model_validate(row.model_dump(exclude={"draft_file_id"}))
        except ValidationError as exc:
            issues.extend(
                RowIssue(field=i["field"], message=i["message"]) for i in field_issues(exc)
            )
        if body is not None:
            if body.job_id not in job_ok:
                try:
                    await _load_job_for_create(session, user, body.job_id)
                    job_ok[body.job_id] = True
                except AppError:
                    job_ok[body.job_id] = False
            if not job_ok[body.job_id]:
                issues.append(RowIssue(field="job_id", message="Job not found"))
        prepared.append(
            _PreparedRow(
                index=index,
                draft_file_id=row.draft_file_id,
                body=body if not issues else None,
                file=file,
                issues=issues,
            )
        )
    return prepared


def _row_link(candidate_id: uuid.UUID, application_id: uuid.UUID | None) -> str:
    base = f"/candidates/{candidate_id}"
    return f"{base}?application={application_id}" if application_id else base


async def _save_row(
    session: AsyncSession, user: User, row: _PreparedRow
) -> tuple[DraftCommitRowOut, str | None]:
    """Create one candidate in its own transaction. Returns the result and the draft key to
    purge (only when the row was saved)."""
    assert row.body is not None  # noqa: S101 - callers only pass valid rows
    try:
        data = await storage.get_object(row.file.storage_key) if row.file else None
        result = await stage_manual_candidate(
            session, user, row.body, data, row.file.file_name if row.file else None
        )
        if row.file is not None:
            taken = cast(
                "CursorResult[Any]",
                await session.execute(
                    delete(CandidateDraftFile).where(CandidateDraftFile.id == row.file.id)
                ),
            )
            if taken.rowcount == 0:
                raise AppError(status.HTTP_409_CONFLICT, "conflict", "This CV was already saved")
        await session.commit()
    except Exception as exc:
        await session.rollback()
        await session.refresh(user)  # rollback expires it; later rows still need it
        if isinstance(exc, AppError):
            message = exc.message
        elif isinstance(exc, FileNotFoundError):
            message = "The uploaded CV is no longer available. Upload it again."
        else:
            logger.exception("draft_commit_row_failed index=%s", row.index)
            message = "Could not save this candidate"
        return (
            DraftCommitRowOut(
                index=row.index,
                draft_file_id=row.draft_file_id,
                status=RowStatus.FAILED,
                issues=[RowIssue(field="", message=message)],
            ),
            None,
        )
    enqueue_cv_processing(result.document_id)
    return (
        DraftCommitRowOut(
            index=row.index,
            draft_file_id=row.draft_file_id,
            status=RowStatus.SAVED,
            candidate_id=result.candidate_id,
            application_id=result.application_id,
            document_id=result.document_id,
            reference_no=result.reference_no,
            reused=result.reused,
            budget_status=result.budget_status,
            link=_row_link(result.candidate_id, result.application_id),
        ),
        row.file.storage_key if row.file else None,
    )


async def commit_draft(
    session: AsyncSession, user: User, draft_id: uuid.UUID, body: DraftCommitIn
) -> DraftCommitOut:
    """Turn draft rows into candidates.

    `all` is all-or-nothing on validation: any invalid row rejects the request (422) before
    anything is written. `complete_only` saves the valid rows and reports the rest as
    `incomplete`. The draft is deleted once none of its files remain.
    """
    actor_id, org_id = user.id, user.org_id
    draft = await _get_draft(session, user, draft_id)
    draft_pk = draft.id
    file_rows = list(
        await session.scalars(
            select(CandidateDraftFile).where(CandidateDraftFile.draft_id == draft_pk)
        )
    )
    files = {f.id: _FileInfo(f.id, f.storage_key, f.file_name) for f in file_rows}

    prepared = await _prepare_rows(session, user, body.rows, files)
    invalid = [p for p in prepared if p.issues]
    if invalid and body.mode is CommitMode.ALL:
        details: list[dict[str, Any]] = [
            {"row": p.index, "field": i.field, "message": i.message}
            for p in invalid
            for i in p.issues
        ]
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "Some rows are incomplete. Fix them, or save only the complete rows.",
            details,
        )

    results: list[DraftCommitRowOut] = []
    saved_keys: list[str] = []
    for row in prepared:
        if row.issues:
            results.append(
                DraftCommitRowOut(
                    index=row.index,
                    draft_file_id=row.draft_file_id,
                    status=RowStatus.INCOMPLETE,
                    issues=row.issues,
                )
            )
            continue
        out, saved_key = await _save_row(session, user, row)
        results.append(out)
        if saved_key:
            saved_keys.append(saved_key)

    saved = sum(r.status is RowStatus.SAVED for r in results)
    incomplete = sum(r.status is RowStatus.INCOMPLETE for r in results)
    failed = sum(r.status is RowStatus.FAILED for r in results)

    await _purge_keys(session, saved_keys, "draft_committed")

    draft_deleted = False
    if saved:
        remaining = int(
            await session.scalar(
                select(func.count())
                .select_from(CandidateDraftFile)
                .where(CandidateDraftFile.draft_id == draft_pk)
            )
            or 0
        )
        if remaining == 0:
            await _delete_draft_rows(
                session, draft_pk, actor_id=actor_id, action="candidate_draft.committed"
            )
            await _purge_keys(session, await _stray_keys(org_id, draft_pk), "draft_committed")
            draft_deleted = True
        else:
            await write_audit(
                session,
                actor_id=actor_id,
                action="candidate_draft.partially_committed",
                entity_type="candidate_draft",
                entity_id=draft_pk,
                diff={"saved": saved, "remaining_files": remaining},
            )
            await session.commit()
    return DraftCommitOut(
        mode=body.mode,
        results=results,
        saved_count=saved,
        incomplete_count=incomplete,
        failed_count=failed,
        draft_deleted=draft_deleted,
    )
