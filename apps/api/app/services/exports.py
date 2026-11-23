"""HR-only candidate PDF summaries and Excel exports. Files are never stored on disk."""

from __future__ import annotations

import io
import logging
import re
import zipfile
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import scope_jobs_query
from app.core.errors import AppError
from app.core.pagination import PageParams
from app.models import (
    Application,
    AtsCheck,
    Candidate,
    Document,
    Job,
    MatchResult,
    Note,
    ParsedProfile,
    User,
)
from app.models.org_setup import Department, PipelineStage
from app.models.ratings import InterviewRating
from app.schemas.application import ApplicationFilters
from app.schemas.exports import PdfSummaryOptions
from app.services import applications as applications_service
from app.services.compliance import write_audit
from app.services.excel_export import EXCEL_COLUMNS, EXCEL_MAX_ROWS, build_candidates_workbook
from app.services.exports_common import (
    filters_summary,
    format_ctc,
    format_education,
    format_experience,
    profile_data,
    top_skills,
)
from app.services.org import LOGO_KEY, _user_org, org_display_name
from app.services.pdf_summary import build_pdf_summary
from app.services.salary import candidate_budget

logger = logging.getLogger(__name__)

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(text: str, *, fallback: str = "candidate") -> str:
    cleaned = _SAFE_FILENAME.sub("_", text.strip())[:80].strip("._-")
    return cleaned or fallback


def _not_found(entity: str = "Application") -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", f"{entity} not found")


def _forbidden_limit(message: str) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, "export_limit", message)


async def _load_applications_by_ids(
    session: AsyncSession, user: User, application_ids: list[UUID]
) -> list[tuple[Application, Candidate, Job, PipelineStage]]:
    if not application_ids:
        return []
    rows = (
        await session.execute(
            scope_jobs_query(
                user,
                select(Application, Candidate, Job, PipelineStage)
                .join(Job, Job.id == Application.job_id)
                .join(Candidate, Candidate.id == Application.candidate_id)
                .join(PipelineStage, PipelineStage.id == Application.stage_id)
                .where(
                    Application.id.in_(application_ids),
                    Candidate.deleted_at.is_(None),
                ),
            )
        )
    ).all()
    by_id = {row[0].id: (row[0], row[1], row[2], row[3]) for row in rows}
    missing = [i for i in application_ids if i not in by_id]
    if missing:
        raise _not_found("Application")
    return [by_id[i] for i in application_ids]


async def _department_name(session: AsyncSession, candidate: Candidate, job: Job) -> str:
    dept_id = candidate.department_id or job.department_id
    if dept_id is None:
        return ""
    dept = await session.get(Department, dept_id)
    return dept.name if dept else ""


async def _latest_match(session: AsyncSession, application_id: UUID) -> MatchResult | None:
    result: MatchResult | None = await session.scalar(
        select(MatchResult)
        .where(MatchResult.application_id == application_id)
        .order_by(MatchResult.computed_at.desc())
        .limit(1)
    )
    return result


async def _latest_ats(session: AsyncSession, candidate_id: UUID) -> AtsCheck | None:
    result: AtsCheck | None = await session.scalar(
        select(AtsCheck)
        .join(Document, Document.id == AtsCheck.document_id)
        .where(Document.candidate_id == candidate_id)
        .order_by(AtsCheck.created_at.desc())
        .limit(1)
    )
    return result


async def _parsed_profile(session: AsyncSession, candidate_id: UUID) -> ParsedProfile | None:
    result: ParsedProfile | None = await session.scalar(
        select(ParsedProfile)
        .where(ParsedProfile.candidate_id == candidate_id)
        .order_by(ParsedProfile.updated_at.desc())
        .limit(1)
    )
    return result


async def _interview_ratings(session: AsyncSession, application_id: UUID) -> list[InterviewRating]:
    return list(
        await session.scalars(
            select(InterviewRating)
            .where(InterviewRating.application_id == application_id)
            .order_by(InterviewRating.interviewed_at.desc())
        )
    )


async def _hr_note_bodies(session: AsyncSession, candidate_id: UUID) -> list[str]:
    notes = await session.scalars(
        select(Note)
        .where(Note.candidate_id == candidate_id)
        .order_by(Note.created_at.desc())
        .limit(20)
    )
    return [n.body.strip() for n in notes if n.body and n.body.strip()]


async def _pdf_payload(
    session: AsyncSession,
    user: User,
    application: Application,
    candidate: Candidate,
    job: Job,
    stage: PipelineStage,
    options: PdfSummaryOptions,
) -> dict[str, Any]:
    org = await _user_org(session, user)
    match = await _latest_match(session, application.id)
    ats = await _latest_ats(session, candidate.id)
    profile = await _parsed_profile(session, candidate.id)
    ratings = await _interview_ratings(session, application.id)
    data = profile_data(
        profile.data if profile else None,
        profile.corrected_data if profile else None,
    )
    missing = []
    if match:
        missing = list(match.missing_required or []) + list(match.missing_preferred or [])

    payload: dict[str, Any] = {
        "org_name": org_display_name(org),
        "org_logo_data_url": (org.settings or {}).get(LOGO_KEY) if org else None,
        "candidate_name": f"{candidate.first_name} {candidate.last_name}".strip(),
        "current_title": candidate.current_title or "",
        "current_company": candidate.current_company or "",
        "job_title": job.title,
        "department": await _department_name(session, candidate, job),
        "stage": stage.name,
        "is_shortlisted": application.is_shortlisted,
        "include_contact": options.include_contact,
        "include_salary": options.include_salary,
        "include_hr_notes": options.include_hr_notes,
        "email": candidate.email if options.include_contact else "",
        "phone": (candidate.phone or "") if options.include_contact else "",
        "location": (candidate.current_location or "") if options.include_contact else "",
        "current_ctc": format_ctc(
            candidate.current_ctc, candidate.current_ctc_currency, candidate.current_ctc_unit.value
        )
        if options.include_salary
        else "",
        "expected_ctc": format_ctc(
            candidate.expected_ctc,
            candidate.expected_ctc_currency,
            candidate.expected_ctc_unit.value,
        )
        if options.include_salary
        else "",
        "offered_ctc": format_ctc(
            candidate.offered_ctc, candidate.offered_ctc_currency, candidate.offered_ctc_unit.value
        )
        if options.include_salary
        else "",
        "total_experience_years": (
            float(candidate.total_experience_years)
            if candidate.total_experience_years is not None
            else None
        ),
        "experience_lines": format_experience(data),
        "education_lines": format_education(data),
        "top_skills": top_skills(data),
        "match_score": match.overall_score if match else None,
        "matched_skills": list(match.matched_skills or []) if match else [],
        "missing_skills": missing,
        "ats_score": ats.score if ats else None,
        "interview_ratings": [
            {
                "round_name": r.round_name,
                "overall_rating": r.overall_rating,
                "recommendation": r.recommendation.value if r.recommendation else "",
                "skill_ratings": list(r.skill_ratings or []),
                "strengths": r.strengths or "",
                "concerns": r.concerns or "",
            }
            for r in ratings
        ],
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    }
    if options.include_hr_notes:
        payload["hr_notes"] = await _hr_note_bodies(session, candidate.id)
    return payload


async def export_pdf_summaries(
    session: AsyncSession,
    user: User,
    application_ids: list[UUID],
    options: PdfSummaryOptions,
) -> tuple[bytes, str, str]:
    """Return (content, media_type, filename). Never writes the file to storage."""
    rows = await _load_applications_by_ids(session, user, application_ids)
    pdfs: list[tuple[str, bytes]] = []
    for application, candidate, job, stage in rows:
        payload = await _pdf_payload(session, user, application, candidate, job, stage, options)
        pdf_bytes = build_pdf_summary(payload)
        name = _safe_name(
            f"{candidate.first_name}_{candidate.last_name}_{job.title}",
            fallback=str(application.id),
        )
        pdfs.append((f"{name}.pdf", pdf_bytes))

    await write_audit(
        session,
        actor_id=user.id,
        action="candidates.pdf_exported",
        entity_type="application",
        entity_id=application_ids[0] if len(application_ids) == 1 else None,
        diff={
            "count": len(application_ids),
            "include_salary": options.include_salary,
            "include_contact": options.include_contact,
            "include_hr_notes": options.include_hr_notes,
            "format": "pdf" if len(pdfs) == 1 else "zip",
        },
    )
    await session.commit()
    logger.info(
        "pdf_export user_id=%s count=%s format=%s",
        user.id,
        len(application_ids),
        "pdf" if len(pdfs) == 1 else "zip",
    )

    if len(pdfs) == 1:
        return pdfs[0][1], "application/pdf", pdfs[0][0]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        used: set[str] = set()
        for filename, content in pdfs:
            final = filename
            n = 1
            while final in used:
                stem = filename[:-4] if filename.endswith(".pdf") else filename
                final = f"{stem}_{n}.pdf"
                n += 1
            used.add(final)
            zf.writestr(final, content)
    return buf.getvalue(), "application/zip", "candidate-summaries.zip"


async def _excel_row(
    session: AsyncSession,
    application: Application,
    candidate: Candidate,
    job: Job,
    stage: PipelineStage,
    match_score: int | None,
) -> dict[str, Any]:
    ats = await _latest_ats(session, candidate.id)
    ratings = await _interview_ratings(session, application.id)
    recommendation = ""
    if ratings:
        recommendation = ratings[0].recommendation.value if ratings[0].recommendation else ""
    budget = candidate_budget(candidate, job.salary_max, job.salary_min)
    dept = await _department_name(session, candidate, job)
    name = f"{candidate.first_name} {candidate.last_name}".strip()
    return {
        "Name": name,
        "Email": candidate.email,
        "Phone": candidate.phone or "",
        "Location": candidate.current_location or "",
        "Job": job.title,
        "Department": dept,
        "Stage": stage.name,
        "Source": candidate.source.value if candidate.source else "",
        "Current company": candidate.current_company or "",
        "Current title": candidate.current_title or "",
        "Total experience": (
            float(candidate.total_experience_years)
            if candidate.total_experience_years is not None
            else ""
        ),
        "Notice period (days)": candidate.notice_period_days
        if candidate.notice_period_days is not None
        else "",
        "Current CTC": format_ctc(
            candidate.current_ctc, candidate.current_ctc_currency, candidate.current_ctc_unit.value
        ),
        "Expected CTC": format_ctc(
            candidate.expected_ctc,
            candidate.expected_ctc_currency,
            candidate.expected_ctc_unit.value,
        ),
        "Offered CTC": format_ctc(
            candidate.offered_ctc, candidate.offered_ctc_currency, candidate.offered_ctc_unit.value
        ),
        "Above budget": "Yes" if budget.value == "above" else "No",
        "Match score": match_score if match_score is not None else "",
        "ATS score": ats.score if ats else "",
        "Average interview rating": (
            float(application.overall_rating) if application.overall_rating is not None else ""
        ),
        "Recommendation": recommendation,
        "Shortlisted": "Yes" if application.is_shortlisted else "No",
        "Tags": ", ".join(candidate.tags or []),
        "Applied date": application.applied_at.date().isoformat(),
    }


async def export_excel(
    session: AsyncSession,
    user: User,
    *,
    filters: ApplicationFilters,
    sort: str | None,
    application_ids: list[UUID] | None = None,
) -> tuple[bytes, str]:
    """Return (xlsx_bytes, filename). Raises export_limit when over EXCEL_MAX_ROWS."""
    selection_mode = "selected" if application_ids else "filters"

    if application_ids:
        if len(application_ids) > EXCEL_MAX_ROWS:
            raise _forbidden_limit(
                f"Excel export is limited to {EXCEL_MAX_ROWS:,} rows. "
                f"You selected {len(application_ids):,}."
            )
        ids = list(application_ids)
        filter_meta = {"selection": f"{len(ids)} application id(s)"}
    else:
        # Reuse list_applications so export filters stay identical to the Candidates page.
        # page_size max is 100 on the public API; use the service directly with a higher cap.
        params = PageParams(page=1, page_size=EXCEL_MAX_ROWS + 1, sort=sort)
        items, total = await applications_service.list_applications(session, user, params, filters)
        if total > EXCEL_MAX_ROWS:
            raise _forbidden_limit(
                f"Excel export is limited to {EXCEL_MAX_ROWS:,} rows. "
                f"The current filters match {total:,}. Narrow the filters or export a selection."
            )
        ids = [item.id for item in items]
        filter_meta = filters_summary(filters)

    loaded = await _load_applications_by_ids(session, user, ids) if ids else []
    excel_rows: list[dict[str, Any]] = []
    for application, candidate, job, stage in loaded:
        match = await _latest_match(session, application.id)
        excel_rows.append(
            await _excel_row(
                session,
                application,
                candidate,
                job,
                stage,
                match.overall_score if match else None,
            )
        )

    content = build_candidates_workbook(
        excel_rows,
        filters_used=filter_meta,
        selection_mode=selection_mode,
    )
    if excel_rows and not set(EXCEL_COLUMNS).issubset(excel_rows[0].keys()):
        raise AppError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "export_error",
            "Export column mismatch",
        )

    await write_audit(
        session,
        actor_id=user.id,
        action="candidates.excel_exported",
        entity_type="application",
        entity_id=None,
        diff={
            "row_count": len(excel_rows),
            "selection_mode": selection_mode,
            "filter_keys": sorted(filter_meta.keys()),
        },
    )
    await session.commit()
    logger.info(
        "excel_export user_id=%s rows=%s mode=%s",
        user.id,
        len(excel_rows),
        selection_mode,
    )
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return content, f"candidates-export-{stamp}.xlsx"
