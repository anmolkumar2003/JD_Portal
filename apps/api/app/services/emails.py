"""Email templates, preview, send, stage triggers (COMM-01/02, PIPE-03)."""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    ActivityLog,
    Application,
    Candidate,
    EmailLog,
    EmailTemplate,
    Job,
    Organization,
    PipelineStage,
    User,
)
from app.schemas.comms import (
    EmailLogOut,
    EmailPreviewIn,
    EmailPreviewOut,
    EmailSendIn,
    EmailTemplateIn,
    EmailTemplateOut,
)
from app.services.org import org_display_name
from app.workers.tasks import send_email

logger = logging.getLogger(__name__)

VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_template(text: str, variables: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return VAR_RE.sub(repl, text)


async def list_templates(session: AsyncSession, user: User) -> list[EmailTemplateOut]:
    rows = await session.scalars(
        select(EmailTemplate).where(EmailTemplate.org_id == user.org_id).order_by(EmailTemplate.key)
    )
    return [EmailTemplateOut.model_validate(r) for r in rows]


async def upsert_template(
    session: AsyncSession, user: User, body: EmailTemplateIn, template_id: uuid.UUID | None = None
) -> EmailTemplateOut:
    if template_id:
        row = await session.get(EmailTemplate, template_id)
        if row is None or row.org_id != user.org_id:
            raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Template not found")
    else:
        row = EmailTemplate(org_id=user.org_id)
        session.add(row)
    row.key = body.key
    row.subject = body.subject
    row.body_html = body.body_html
    row.variables = body.variables
    row.trigger_stage_id = body.trigger_stage_id
    row.is_active = body.is_active
    await session.commit()
    await session.refresh(row)
    return EmailTemplateOut.model_validate(row)


def preview(body: EmailPreviewIn) -> EmailPreviewOut:
    return EmailPreviewOut(
        subject=render_template(body.subject, body.variables),
        body_html=render_template(body.body_html, body.variables),
    )


async def _context(
    session: AsyncSession, candidate_id: uuid.UUID, application_id: uuid.UUID | None
) -> dict[str, str]:
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None:
        return {}
    ctx: dict[str, str] = {
        "org_name": org_display_name(await session.get(Organization, candidate.org_id)),
        "candidate_name": f"{candidate.first_name} {candidate.last_name}".strip(),
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
    }
    if application_id:
        app = await session.get(Application, application_id)
        if app:
            job = await session.get(Job, app.job_id)
            if job:
                ctx["job_title"] = job.title
            ctx["reference_no"] = app.reference_no
    return ctx


async def send_candidate_email(session: AsyncSession, user: User, body: EmailSendIn) -> EmailLogOut:
    candidate = await session.get(Candidate, body.candidate_id)
    if candidate is None or candidate.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    ctx = await _context(session, body.candidate_id, body.application_id)
    subject = render_template(body.subject, ctx)
    content = render_template(body.body, ctx)
    to_addr = body.to or candidate.email
    log = EmailLog(
        candidate_id=candidate.id,
        application_id=body.application_id,
        template_key=body.template_key,
        to_address=to_addr,
        subject=subject,
        body=content,
        status="queued",
        sent_by=user.id,
    )
    session.add(log)
    session.add(
        ActivityLog(
            candidate_id=candidate.id,
            application_id=body.application_id,
            actor_id=user.id,
            action="email.sent",
            meta={"template_key": body.template_key},
        )
    )
    await session.commit()
    await session.refresh(log)
    try:
        send_email.delay(to_addr, subject, content)
        log.status = "sent"
        await session.commit()
    except Exception:
        logger.exception("email_queue_failed")
        log.status = "failed"
        await session.commit()
    return EmailLogOut.model_validate(log)


async def list_candidate_emails(
    session: AsyncSession, user: User, candidate_id: uuid.UUID
) -> list[EmailLogOut]:
    candidate = await session.get(Candidate, candidate_id)
    if candidate is None or candidate.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")
    rows = await session.scalars(
        select(EmailLog)
        .where(EmailLog.candidate_id == candidate_id)
        .order_by(EmailLog.sent_at.desc())
    )
    return [EmailLogOut.model_validate(r) for r in rows]


async def maybe_send_stage_email(
    session: AsyncSession, user: User, application: Application, stage: PipelineStage
) -> None:
    """PIPE-03: auto-send if a template is linked to the stage. Rejection templates stay off
    unless explicitly activated (is_active and trigger set)."""
    if stage.type.value == "rejected":
        # Off by default: only fire if an active template is explicitly linked.
        pass
    template = await session.scalar(
        select(EmailTemplate).where(
            EmailTemplate.org_id == user.org_id,
            EmailTemplate.trigger_stage_id == stage.id,
            EmailTemplate.is_active.is_(True),
        )
    )
    if template is None:
        return
    candidate = await session.get(Candidate, application.candidate_id)
    if candidate is None:
        return
    await send_candidate_email(
        session,
        user,
        EmailSendIn(
            candidate_id=candidate.id,
            application_id=application.id,
            template_key=template.key,
            subject=template.subject,
            body=template.body_html,
        ),
    )
