"""Offers and hired flow (OFFER-01..03, OFFER-05)."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.deps import can_access_job
from app.core.errors import AppError
from app.models import Application, Candidate, Document, Job, PipelineStage, User
from app.models.enums import ApplicationStatus, DocumentType, JobStatus, StageType
from app.models.hiring import Offer, OfferStatus


def _render_offer_pdf(
    *,
    candidate_name: str,
    designation: str,
    ctc: dict[str, Any],
    joining_date: date | None,
) -> bytes:
    """Generate a simple offer letter PDF locally (reportlab)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        # Fallback plain-text "PDF" bytes for environments without reportlab
        text = (
            f"Offer Letter\n\nDear {candidate_name},\n\n"
            f"We are pleased to offer you the role of {designation}.\n"
            f"CTC: {ctc}\nJoining: {joining_date}\n"
        )
        return text.encode("utf-8")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _, height = A4
    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, "Offer of Employment")
    y -= 36
    c.setFont("Helvetica", 11)
    for line in [
        f"Dear {candidate_name},",
        "",
        f"We are pleased to offer you the position of {designation}.",
        f"Compensation (CTC breakdown): {ctc}",
        f"Proposed joining date: {joining_date or 'TBD'}",
        "",
        "This offer is subject to standard background checks and approvals.",
        "",
        "Sincerely,",
        "People Operations",
    ]:
        c.drawString(72, y, line[:100])
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


async def create_offer(
    session: AsyncSession,
    user: User,
    *,
    application_id: uuid.UUID,
    designation: str,
    ctc_breakdown: dict[str, Any],
    joining_date: date | None,
    approval_chain: list[dict[str, Any]],
) -> dict[str, Any]:
    app = await session.get(Application, application_id)
    if app is None or not await can_access_job(session, user, app.job_id):
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")
    offer = Offer(
        application_id=application_id,
        designation=designation,
        ctc_breakdown=ctc_breakdown,
        joining_date=joining_date,
        approval_chain=approval_chain,
        created_by=user.id,
        status=OfferStatus.DRAFT,
    )
    session.add(offer)
    await session.commit()
    await session.refresh(offer)
    return {"id": str(offer.id), "status": offer.status.value}


async def submit_for_approval(
    session: AsyncSession, user: User, offer_id: uuid.UUID
) -> dict[str, Any]:
    offer = await session.get(Offer, offer_id)
    if offer is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Offer not found")
    offer.status = OfferStatus.PENDING_APPROVAL
    await session.commit()
    return {"id": str(offer.id), "status": offer.status.value}


async def approve_offer(session: AsyncSession, user: User, offer_id: uuid.UUID) -> dict[str, Any]:
    offer = await session.get(Offer, offer_id)
    if offer is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Offer not found")
    offer.status = OfferStatus.APPROVED
    await session.commit()
    return {"id": str(offer.id), "status": offer.status.value}


async def send_offer(session: AsyncSession, user: User, offer_id: uuid.UUID) -> dict[str, Any]:
    offer = await session.get(Offer, offer_id)
    if offer is None or offer.status not in {OfferStatus.APPROVED, OfferStatus.SENT}:
        raise AppError(status.HTTP_400_BAD_REQUEST, "invalid_status", "Offer not approved")
    app = await session.get(Application, offer.application_id)
    if app is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")
    candidate = await session.get(Candidate, app.candidate_id)
    if candidate is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Candidate not found")

    pdf = _render_offer_pdf(
        candidate_name=f"{candidate.first_name} {candidate.last_name}",
        designation=offer.designation,
        ctc=offer.ctc_breakdown,
        joining_date=offer.joining_date,
    )
    document_id = uuid.uuid4()
    storage_key = f"{user.org_id}/{candidate.id}/{document_id}.pdf"
    await storage.put_object(storage_key, pdf, "application/pdf")
    session.add(
        Document(
            id=document_id,
            candidate_id=candidate.id,
            application_id=app.id,
            type=DocumentType.OFFER,
            file_name=f"offer-{offer.designation.replace(' ', '-')}.pdf",
            mime_type="application/pdf",
            size=len(pdf),
            storage_key=storage_key,
            checksum="",
            is_primary=False,
        )
    )
    offer.document_id = document_id
    offer.status = OfferStatus.SENT
    offer.sent_at = datetime.now(UTC)
    await session.commit()
    return {"id": str(offer.id), "status": offer.status.value, "document_id": str(document_id)}


async def accept_offer(session: AsyncSession, user: User, offer_id: uuid.UUID) -> dict[str, Any]:
    """OFFER-05: mark hired, decrement openings, auto-close job at zero."""
    offer = await session.get(Offer, offer_id)
    if offer is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Offer not found")
    app = await session.get(Application, offer.application_id)
    if app is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Application not found")
    job = await session.get(Job, app.job_id)
    if job is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Job not found")

    hired_stage = await session.scalar(
        select(PipelineStage).where(
            PipelineStage.org_id == user.org_id, PipelineStage.type == StageType.HIRED
        )
    )
    offer.status = OfferStatus.ACCEPTED
    offer.responded_at = datetime.now(UTC)
    app.status = ApplicationStatus.HIRED
    if hired_stage:
        app.stage_id = hired_stage.id
        app.stage_entered_at = datetime.now(UTC)
    if job.openings > 0:
        job.openings -= 1
    if job.openings <= 0:
        job.status = JobStatus.FILLED
    await session.commit()
    return {
        "id": str(offer.id),
        "status": offer.status.value,
        "job_openings": job.openings,
        "job_status": job.status.value,
    }
