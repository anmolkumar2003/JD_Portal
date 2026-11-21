"""Interview scheduling and scorecards (INT-01..04, INT-06)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import can_access_job
from app.core.errors import AppError
from app.models import Application, Candidate, Job, User
from app.models.interviews import (
    Interview,
    InterviewMode,
    InterviewPanel,
    InterviewType,
    Recommendation,
    Scorecard,
    ScorecardTemplate,
)
from app.schemas.comms import EmailSendIn
from app.services.emails import send_candidate_email
from app.workers.tasks import send_email


def _ics(interview: Interview, candidate_name: str, job_title: str) -> str:
    uid = f"{interview.id}@hr-portal.local"
    start = interview.scheduled_at.strftime("%Y%m%dT%H%M%SZ")
    return "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//HR Portal//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start}",
            f"SUMMARY:{interview.round_name} — {job_title}",
            f"DESCRIPTION:Interview with {candidate_name}",
            f"LOCATION:{interview.meeting_link or interview.location or ''}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )


async def create_interview(
    session: AsyncSession,
    user: User,
    *,
    application_id: uuid.UUID,
    round_name: str,
    type: InterviewType,
    mode: InterviewMode,
    scheduled_at: datetime,
    duration_min: int,
    panel_user_ids: list[uuid.UUID],
    meeting_link: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    app = await session.get(Application, application_id)
    if app is None or not await can_access_job(session, user, app.job_id):
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")
    interview = Interview(
        application_id=application_id,
        round_name=round_name,
        type=type,
        mode=mode,
        scheduled_at=scheduled_at,
        duration_min=duration_min,
        meeting_link=meeting_link,
        location=location,
        created_by=user.id,
    )
    session.add(interview)
    await session.flush()
    for uid in panel_user_ids:
        session.add(InterviewPanel(interview_id=interview.id, user_id=uid))
    await session.commit()
    await session.refresh(interview)

    candidate = await session.get(Candidate, app.candidate_id)
    job = await session.get(Job, app.job_id)
    if candidate and job:
        ics = _ics(interview, f"{candidate.first_name} {candidate.last_name}", job.title)
        for uid in panel_user_ids:
            panel_user = await session.get(User, uid)
            if panel_user:
                try:
                    send_email.delay(
                        panel_user.email,
                        f"Interview: {interview.round_name}",
                        f"You are on the panel.\n\n{ics}",
                    )
                except Exception:
                    pass
        try:
            await send_candidate_email(
                session,
                user,
                EmailSendIn(
                    candidate_id=candidate.id,
                    application_id=app.id,
                    subject=f"Interview scheduled: {interview.round_name}",
                    body=f"Hi {candidate.first_name},\n\nYour interview is scheduled.\n\n{ics}",
                ),
            )
        except Exception:
            pass

    return {"id": str(interview.id), "status": interview.status.value}


async def my_interviews(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Interview, Application, Candidate, Job)
            .join(InterviewPanel, InterviewPanel.interview_id == Interview.id)
            .join(Application, Application.id == Interview.application_id)
            .join(Candidate, Candidate.id == Application.candidate_id)
            .join(Job, Job.id == Application.job_id)
            .where(InterviewPanel.user_id == user.id)
            .order_by(Interview.scheduled_at)
        )
    ).all()
    return [
        {
            "id": str(interview.id),
            "round_name": interview.round_name,
            "scheduled_at": interview.scheduled_at.isoformat(),
            "status": interview.status.value,
            "candidate": f"{candidate.first_name} {candidate.last_name}",
            "job_title": job.title,
            "application_id": str(app.id),
        }
        for interview, app, candidate, job in rows
    ]


async def submit_scorecard(
    session: AsyncSession,
    user: User,
    interview_id: uuid.UUID,
    *,
    ratings: dict[str, Any],
    comments: str | None,
    recommendation: Recommendation,
) -> dict[str, Any]:
    panel = await session.scalar(
        select(InterviewPanel).where(
            InterviewPanel.interview_id == interview_id, InterviewPanel.user_id == user.id
        )
    )
    if panel is None:
        raise AppError(status.HTTP_403_FORBIDDEN, "forbidden", "Not on this interview panel")
    card = await session.scalar(
        select(Scorecard).where(
            Scorecard.interview_id == interview_id, Scorecard.interviewer_id == user.id
        )
    )
    if card is None:
        card = Scorecard(interview_id=interview_id, interviewer_id=user.id)
        session.add(card)
    card.ratings = ratings
    card.comments = comments
    card.recommendation = recommendation
    card.submitted_at = datetime.now(UTC)
    panel.feedback_submitted_at = card.submitted_at
    await session.commit()
    return {"interview_id": str(interview_id), "submitted_at": card.submitted_at.isoformat()}


async def interview_summary(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> dict[str, Any]:
    app = await session.get(Application, application_id)
    if app is None or not await can_access_job(session, user, app.job_id):
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")
    interviews = list(
        await session.scalars(
            select(Interview).where(Interview.application_id == application_id)
        )
    )
    cards: list[dict[str, Any]] = []
    for interview in interviews:
        my_panel = await session.scalar(
            select(InterviewPanel).where(
                InterviewPanel.interview_id == interview.id, InterviewPanel.user_id == user.id
            )
        )
        submitted = my_panel is not None and my_panel.feedback_submitted_at is not None
        # INT-04: hide others until this interviewer has submitted
        scorecards = list(
            await session.scalars(
                select(Scorecard).where(
                    Scorecard.interview_id == interview.id, Scorecard.submitted_at.is_not(None)
                )
            )
        )
        visible = scorecards if submitted or my_panel is None else [
            s for s in scorecards if s.interviewer_id == user.id
        ]
        cards.append(
            {
                "interview_id": str(interview.id),
                "round_name": interview.round_name,
                "scorecards": [
                    {
                        "interviewer_id": str(s.interviewer_id),
                        "ratings": s.ratings,
                        "recommendation": s.recommendation.value if s.recommendation else None,
                        "comments": s.comments if submitted or s.interviewer_id == user.id else None,
                    }
                    for s in visible
                ],
            }
        )
    return {"application_id": str(application_id), "interviews": cards}


async def list_scorecard_templates(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    rows = await session.scalars(
        select(ScorecardTemplate).where(ScorecardTemplate.org_id == user.org_id)
    )
    return [{"id": str(r.id), "name": r.name, "competencies": r.competencies} for r in rows]
