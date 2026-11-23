"""Notes with @mentions, tags, shortlist and bulk actions. CAND-05, CAND-06."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ORG_WIDE_JOB_ROLES, scope_jobs_query
from app.core.errors import AppError
from app.models import ActivityLog, Application, Candidate, Job, Note, PipelineStage, User
from app.models.enums import StageType
from app.schemas.application import StagePatch
from app.schemas.candidate_actions import (
    MAX_TAGS,
    BulkActionRequest,
    BulkActionResult,
    BulkActionType,
    BulkFailure,
    CandidateOut,
    CandidatePatch,
    CandidateTagsOut,
    NoteCreate,
    NoteOut,
    ShortlistOut,
    UserRef,
)
from app.services.applications import _get_scoped_application, apply_stage_change
from app.services.salary import (
    apply_salary,
    current_salary,
    expected_salary,
    offered_salary,
)


def _candidate_not_found() -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")


def _user_ref(user: User) -> UserRef:
    return UserRef(id=user.id, full_name=user.full_name, role=user.role)


def normalize_tags(tags: Iterable[str]) -> list[str]:
    """Trim, drop blanks and de-duplicate case-insensitively, keeping the first spelling."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in tags:
        tag = raw.strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            result.append(tag)
    return result


async def _accessible_candidate(
    session: AsyncSession, user: User, candidate_id: uuid.UUID
) -> Candidate:
    """Org-wide roles see any candidate; others need at least one accessible application."""
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None or candidate.deleted_at is not None or candidate.org_id != user.org_id:
        raise _candidate_not_found()
    if user.role in ORG_WIDE_JOB_ROLES:
        return candidate
    accessible = await session.scalar(
        scope_jobs_query(
            user,
            select(Application.id)
            .join(Job, Job.id == Application.job_id)
            .where(Application.candidate_id == candidate_id)
            .limit(1),
        )
    )
    if accessible is None:
        raise _candidate_not_found()
    return candidate


# --- Users for @mentions ----------------------------------------------------------------------


async def lookup_users(session: AsyncSession, user: User) -> list[UserRef]:
    rows = await session.scalars(
        select(User)
        .where(User.org_id == user.org_id, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return [_user_ref(u) for u in rows]


# --- Notes (CAND-05) --------------------------------------------------------------------------


async def _note_out(session: AsyncSession, notes: list[Note]) -> list[NoteOut]:
    user_ids = {n.author_id for n in notes} | {m for n in notes for m in n.mentions}
    users: dict[uuid.UUID, User] = {}
    if user_ids:
        users = {u.id: u for u in await session.scalars(select(User).where(User.id.in_(user_ids)))}
    return [
        NoteOut(
            id=n.id,
            candidate_id=n.candidate_id,
            application_id=n.application_id,
            author=_user_ref(users[n.author_id]) if n.author_id in users else None,
            body=n.body,
            mentions=[_user_ref(users[m]) for m in n.mentions if m in users],
            created_at=n.created_at,
        )
        for n in notes
    ]


async def list_notes(session: AsyncSession, user: User, candidate_id: uuid.UUID) -> list[NoteOut]:
    await _accessible_candidate(session, user, candidate_id)
    notes = list(
        await session.scalars(
            select(Note)
            .where(Note.candidate_id == candidate_id)
            .order_by(Note.created_at.desc())
            .limit(200)
        )
    )
    return await _note_out(session, notes)


async def create_note(
    session: AsyncSession, user: User, candidate_id: uuid.UUID, body: NoteCreate
) -> NoteOut:
    candidate = await _accessible_candidate(session, user, candidate_id)

    if body.application_id is not None:
        application = await session.get(Application, body.application_id)
        if application is None or application.candidate_id != candidate.id:
            raise AppError(
                status.HTTP_400_BAD_REQUEST, "invalid_application", "Unknown application"
            )

    mention_ids = list(dict.fromkeys(body.mentions))
    if mention_ids:
        valid = set(
            await session.scalars(
                select(User.id).where(
                    User.id.in_(mention_ids),
                    User.org_id == user.org_id,
                    User.is_active.is_(True),
                )
            )
        )
        if len(valid) != len(mention_ids):
            raise AppError(
                status.HTTP_400_BAD_REQUEST,
                "invalid_mention",
                "One or more mentioned users do not exist",
            )

    note = Note(
        candidate_id=candidate.id,
        application_id=body.application_id,
        author_id=user.id,
        body=body.body,
        mentions=mention_ids,
    )
    session.add(note)
    await session.flush()
    # The note body is free text that may hold PII, so only ids go into the activity log.
    session.add(
        ActivityLog(
            candidate_id=candidate.id,
            application_id=body.application_id,
            actor_id=user.id,
            action="note.created",
            meta={"note_id": str(note.id), "mentions": [str(m) for m in mention_ids]},
        )
    )
    await session.commit()
    await session.refresh(note)
    return (await _note_out(session, [note]))[0]


# --- Tags (CAND-05) ---------------------------------------------------------------------------


def _check_tag_count(tags: list[str]) -> None:
    if len(tags) > MAX_TAGS:
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            "too_many_tags",
            f"A candidate can have at most {MAX_TAGS} tags",
        )


def _candidate_out(candidate: Candidate) -> CandidateOut:
    return CandidateOut(
        id=candidate.id,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        phone=candidate.phone,
        current_location=candidate.current_location,
        current_company=candidate.current_company,
        current_title=candidate.current_title,
        total_experience_years=candidate.total_experience_years,
        notice_period_days=candidate.notice_period_days,
        linkedin_url=candidate.linkedin_url,
        portfolio_url=candidate.portfolio_url,
        department_id=candidate.department_id,
        source=candidate.source,
        tags=list(candidate.tags or []),
        current_salary=current_salary(candidate),
        expected_salary=expected_salary(candidate),
        offered_salary=offered_salary(candidate),
    )


async def set_candidate_tags(
    session: AsyncSession, user: User, candidate_id: uuid.UUID, tags: list[str]
) -> CandidateTagsOut:
    candidate = await _accessible_candidate(session, user, candidate_id)
    new_tags = normalize_tags(tags)
    _check_tag_count(new_tags)
    old_tags = list(candidate.tags or [])
    if new_tags != old_tags:
        candidate.tags = new_tags
        session.add(
            ActivityLog(
                candidate_id=candidate.id,
                actor_id=user.id,
                action="candidate.tags_updated",
                meta={
                    "added": [t for t in new_tags if t not in old_tags],
                    "removed": [t for t in old_tags if t not in new_tags],
                },
            )
        )
        await session.commit()
    return CandidateTagsOut(id=candidate.id, tags=new_tags)


async def update_candidate(
    session: AsyncSession, user: User, candidate_id: uuid.UUID, body: CandidatePatch
) -> CandidateOut:
    """Full profile edit. Only provided fields change; each change is logged."""
    candidate = await _accessible_candidate(session, user, candidate_id)
    changes: dict[str, object] = {}

    scalar_fields = (
        "first_name",
        "last_name",
        "phone",
        "current_location",
        "current_company",
        "current_title",
        "total_experience_years",
        "notice_period_days",
        "department_id",
        "source",
    )
    for field in scalar_fields:
        value = getattr(body, field)
        if value is not None and getattr(candidate, field) != value:
            changes[field] = str(value)
            setattr(candidate, field, value)

    # Explicit null clears LinkedIn / portfolio; omitted fields are left unchanged.
    for url_field in ("linkedin_url", "portfolio_url"):
        if url_field not in body.model_fields_set:
            continue
        value = getattr(body, url_field)
        if getattr(candidate, url_field) != value:
            changes[url_field] = value
            setattr(candidate, url_field, value)

    if body.email is not None:
        email = body.email.lower()
        if email != candidate.email:
            clash = await session.scalar(
                select(Candidate.id).where(
                    Candidate.org_id == user.org_id,
                    Candidate.email == email,
                    Candidate.id != candidate.id,
                    Candidate.deleted_at.is_(None),
                )
            )
            if clash is not None:
                raise AppError(
                    status.HTTP_409_CONFLICT,
                    "duplicate_email",
                    "Another candidate already uses this email",
                )
            changes["email"] = email
            candidate.email = email

    old_tags = list(candidate.tags or [])
    tags_changed: list[str] | None = None
    if body.tags is not None:
        new_tags = normalize_tags(body.tags)
        _check_tag_count(new_tags)
        if new_tags != old_tags:
            tags_changed = new_tags
            changes["tags"] = new_tags
            candidate.tags = new_tags

    for prefix, salary in (
        ("current", body.current_ctc),
        ("expected", body.expected_ctc),
        ("offered", body.offered_ctc),
    ):
        if salary is not None:
            apply_salary(candidate, prefix, salary)
            changes[f"{prefix}_ctc"] = str(salary.amount) if salary.amount is not None else None

    if changes:
        action = "candidate.tags_updated" if set(changes) == {"tags"} else "candidate.updated"
        meta: dict[str, object]
        if action == "candidate.tags_updated" and tags_changed is not None:
            meta = {
                "added": [t for t in tags_changed if t not in old_tags],
                "removed": [t for t in old_tags if t not in tags_changed],
            }
        else:
            meta = {"fields": sorted(changes.keys())}
        session.add(
            ActivityLog(
                candidate_id=candidate.id,
                actor_id=user.id,
                action=action,
                meta=meta,
            )
        )
        await session.commit()
        await session.refresh(candidate)
    return _candidate_out(candidate)


# --- Shortlist (CAND-05) ----------------------------------------------------------------------


async def set_shortlist(
    session: AsyncSession, user: User, application_id: uuid.UUID, shortlisted: bool | None
) -> ShortlistOut:
    application, candidate, _job, _stage = await _get_scoped_application(
        session, user, application_id
    )
    target = (not application.is_shortlisted) if shortlisted is None else shortlisted
    if target != application.is_shortlisted:
        application.is_shortlisted = target
        session.add(
            ActivityLog(
                candidate_id=candidate.id,
                application_id=application.id,
                actor_id=user.id,
                action="application.shortlisted" if target else "application.unshortlisted",
                meta={},
            )
        )
        await session.commit()
    return ShortlistOut(application_id=application.id, is_shortlisted=target)


# --- Bulk actions (CAND-06) -------------------------------------------------------------------


async def bulk_action(
    session: AsyncSession, user: User, body: BulkActionRequest
) -> BulkActionResult:
    """Apply one action to many applications. Items fail independently; the rest still apply."""
    payload = body.payload
    reject_stage_id: uuid.UUID | None = None
    if body.action == BulkActionType.REJECT:
        rejected = await session.scalar(
            select(PipelineStage)
            .where(PipelineStage.org_id == user.org_id, PipelineStage.type == StageType.REJECTED)
            .order_by(PipelineStage.order)
            .limit(1)
        )
        if rejected is None:
            raise AppError(
                status.HTTP_409_CONFLICT, "no_rejected_stage", "No Rejected stage is configured"
            )
        reject_stage_id = rejected.id

    succeeded: list[uuid.UUID] = []
    failed: list[BulkFailure] = []
    touched_candidates: set[uuid.UUID] = set()

    for application_id in dict.fromkeys(body.ids):
        try:
            application, candidate, _job, stage = await _get_scoped_application(
                session, user, application_id
            )
            if body.action == BulkActionType.TAG:
                if candidate.id not in touched_candidates:
                    touched_candidates.add(candidate.id)
                    _apply_tag_changes(
                        session, user, candidate, payload.add_tags, payload.remove_tags
                    )
            else:
                target = (
                    payload.stage_id
                    if body.action == BulkActionType.MOVE_STAGE
                    else reject_stage_id
                )
                if target is None:
                    raise AppError(status.HTTP_400_BAD_REQUEST, "invalid_stage", "Missing stage")
                await apply_stage_change(
                    session,
                    user,
                    application,
                    candidate,
                    stage,
                    StagePatch(stage_id=target, reason=payload.reason),
                )
            succeeded.append(application_id)
        except AppError as exc:
            failed.append(BulkFailure(id=application_id, code=exc.code, message=exc.message))
    await session.commit()
    return BulkActionResult(action=body.action, succeeded=succeeded, failed=failed)


def _apply_tag_changes(
    session: AsyncSession,
    user: User,
    candidate: Candidate,
    add: list[str],
    remove: list[str],
) -> None:
    old_tags = list(candidate.tags or [])
    removal = {t.lower() for t in remove}
    new_tags = normalize_tags([*(t for t in old_tags if t.lower() not in removal), *add])
    _check_tag_count(new_tags)
    if new_tags == old_tags:
        return
    candidate.tags = new_tags
    session.add(
        ActivityLog(
            candidate_id=candidate.id,
            actor_id=user.id,
            action="candidate.tags_updated",
            meta={
                "added": [t for t in new_tags if t not in old_tags],
                "removed": [t for t in old_tags if t not in new_tags],
                "bulk": True,
            },
        )
    )
