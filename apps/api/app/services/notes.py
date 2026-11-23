"""Candidate notes with @mentions (CAND-05)."""

from __future__ import annotations

import re
import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import can_access_job
from app.core.errors import AppError
from app.models import ActivityLog, Application, Candidate, Note, Notification, User
from app.schemas.comms import NoteCreate, NoteOut

MENTION_RE = re.compile(r"@\[([0-9a-fA-F-]{36})\]")


async def _ensure_candidate_access(session: AsyncSession, user: User, candidate_id: uuid.UUID) -> Candidate:
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None or candidate.deleted_at is not None or candidate.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    app = await session.scalar(
        select(Application).where(Application.candidate_id == candidate_id).limit(1)
    )
    if app is not None and not await can_access_job(session, user, app.job_id):
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    return candidate


def _parse_mentions(body: str, explicit: list[uuid.UUID]) -> list[uuid.UUID]:
    found = [uuid.UUID(m) for m in MENTION_RE.findall(body)]
    return list(dict.fromkeys([*explicit, *found]))


async def list_notes(session: AsyncSession, user: User, candidate_id: uuid.UUID) -> list[NoteOut]:
    await _ensure_candidate_access(session, user, candidate_id)
    rows = (
        await session.execute(
            select(Note, User.full_name)
            .join(User, User.id == Note.author_id)
            .where(Note.candidate_id == candidate_id)
            .order_by(Note.created_at.desc())
        )
    ).all()
    return [
        NoteOut(
            id=note.id,
            candidate_id=note.candidate_id,
            application_id=note.application_id,
            author_id=note.author_id,
            author_name=name,
            body=note.body,
            mentions=list(note.mentions or []),
            created_at=note.created_at,
        )
        for note, name in rows
    ]


async def create_note(
    session: AsyncSession, user: User, candidate_id: uuid.UUID, body: NoteCreate
) -> NoteOut:
    await _ensure_candidate_access(session, user, candidate_id)
    mentions = _parse_mentions(body.body, body.mentions)
    note = Note(
        candidate_id=candidate_id,
        application_id=body.application_id,
        author_id=user.id,
        body=body.body,
        mentions=mentions,
    )
    session.add(note)
    session.add(
        ActivityLog(
            candidate_id=candidate_id,
            application_id=body.application_id,
            actor_id=user.id,
            action="note.created",
            meta={"note_id": "pending"},
        )
    )
    for mentioned in mentions:
        if mentioned == user.id:
            continue
        session.add(
            Notification(
                user_id=mentioned,
                type="mention",
                payload={"candidate_id": str(candidate_id), "by": str(user.id)},
            )
        )
    await session.commit()
    await session.refresh(note)
    return NoteOut(
        id=note.id,
        candidate_id=note.candidate_id,
        application_id=note.application_id,
        author_id=note.author_id,
        author_name=user.full_name,
        body=note.body,
        mentions=list(note.mentions or []),
        created_at=note.created_at,
    )
