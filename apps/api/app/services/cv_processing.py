"""Orchestrate extract → parse → ATS → match and persist results. CV-07/08/10."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import storage
from app.cv_engine.ats_check import run_ats_check
from app.cv_engine.extract import extract_text
from app.cv_engine.matcher import match_result_to_breakdown, score_match
from app.cv_engine.parser import RuleBasedParser
from app.cv_engine.types import CandidateMatchInput, JobRequirements, SkillSpec
from app.models import (
    ActivityLog,
    Application,
    AtsCheck,
    Candidate,
    Document,
    Job,
    JobRequirement,
    Location,
    MatchResult,
    ParsedProfile,
)
from app.models.enums import ParseStatus

logger = logging.getLogger(__name__)
PARSER = RuleBasedParser()


def _split_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name:
        return None, None
    parts = full_name.strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _fill_candidate(candidate: Candidate, data: dict[str, Any], years: float | None) -> None:
    """Update only empty candidate fields from parsed data (no PII in logs)."""
    first, last = _split_name(
        data.get("full_name") if isinstance(data.get("full_name"), str) else None
    )
    if not candidate.first_name and first:
        candidate.first_name = first[:100]
    if not candidate.last_name and last:
        candidate.last_name = last[:100]
    email = data.get("email")
    if not candidate.email and isinstance(email, str):
        candidate.email = email.lower()[:255]
    phone = data.get("phone")
    if not candidate.phone and isinstance(phone, str):
        candidate.phone = phone[:50]
    location = data.get("location")
    if not candidate.current_location and isinstance(location, str):
        candidate.current_location = location[:200]
    if candidate.total_experience_years is None and years is not None:
        candidate.total_experience_years = Decimal(str(years))
    links = data.get("links") or []
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, str):
                continue
            lower = link.lower()
            if "linkedin.com" in lower and not candidate.linkedin_url:
                candidate.linkedin_url = link[:500]
            elif not candidate.portfolio_url and lower.startswith("http"):
                candidate.portfolio_url = link[:500]
    if not candidate.current_title and data.get("experience"):
        exp0 = data["experience"][0] if data["experience"] else None
        if isinstance(exp0, dict) and exp0.get("title"):
            candidate.current_title = str(exp0["title"])[:200]
            if not candidate.current_company and exp0.get("company"):
                candidate.current_company = str(exp0["company"])[:200]


def _job_requirements(session: Session, job: Job) -> JobRequirements:
    req = session.scalar(select(JobRequirement).where(JobRequirement.job_id == job.id))
    location_name = None
    if job.location_id:
        loc = session.get(Location, job.location_id)
        if loc:
            location_name = loc.name
    required: list[SkillSpec] = []
    preferred: list[SkillSpec] = []
    certs: list[str] = []
    weights_override = None
    min_exp = max_exp = edu = None
    if req:
        for item in req.required_skills or []:
            if isinstance(item, dict) and item.get("name"):
                required.append(
                    SkillSpec(name=str(item["name"]), weight=float(item.get("weight") or 1))
                )
        for item in req.preferred_skills or []:
            if isinstance(item, dict) and item.get("name"):
                preferred.append(
                    SkillSpec(name=str(item["name"]), weight=float(item.get("weight") or 1))
                )
        min_exp = float(req.min_experience) if req.min_experience is not None else None
        max_exp = float(req.max_experience) if req.max_experience is not None else None
        edu = req.education_level
        certs = [str(c) for c in (req.certifications or [])]
        weights_override = req.weights_override
    return JobRequirements(
        title=job.title,
        required_skills=required,
        preferred_skills=preferred,
        min_experience=min_exp,
        max_experience=max_exp,
        education_level=edu,
        certifications=certs,
        work_mode=job.work_mode.value if job.work_mode else None,
        location_name=location_name,
        weights_override=weights_override,
    )


def _candidate_input(
    candidate: Candidate, data: dict[str, Any], years: float | None
) -> CandidateMatchInput:
    skills = [str(s) for s in (data.get("skills") or [])]
    titles: list[str] = []
    if candidate.current_title:
        titles.append(candidate.current_title)
    for exp in data.get("experience") or []:
        if isinstance(exp, dict) and exp.get("title"):
            titles.append(str(exp["title"]))
    education = []
    for edu in data.get("education") or []:
        if isinstance(edu, dict):
            education.append(
                " ".join(str(edu.get(k) or "") for k in ("degree", "field", "institution"))
            )
    certs = []
    for cert in data.get("certifications") or []:
        if isinstance(cert, dict) and cert.get("name"):
            certs.append(str(cert["name"]))
        elif isinstance(cert, str):
            certs.append(cert)
    return CandidateMatchInput(
        skills=skills,
        titles=titles,
        total_experience_years=(
            float(years)
            if years is not None
            else (
                float(candidate.total_experience_years)
                if candidate.total_experience_years is not None
                else None
            )
        ),
        education_degrees=education,
        certifications=certs,
        location=candidate.current_location
        or (str(data.get("location")) if data.get("location") else None),
        notice_period_days=candidate.notice_period_days,
    )


def _effective_data(profile: ParsedProfile) -> dict[str, Any]:
    base = dict(profile.data or {})
    if profile.corrected_data:
        base.update(profile.corrected_data)
    return base


def score_application(
    session: Session, application: Application, profile: ParsedProfile
) -> MatchResult:
    job = session.get(Job, application.job_id)
    candidate = session.get(Candidate, application.candidate_id)
    if job is None or candidate is None:
        raise RuntimeError("missing_job_or_candidate")
    data = _effective_data(profile)
    years = (
        float(profile.total_experience_years)
        if profile.total_experience_years is not None
        else None
    )
    if data.get("total_experience_years") is not None:
        try:
            years = float(data["total_experience_years"])
        except (TypeError, ValueError):
            pass
    result = score_match(_job_requirements(session, job), _candidate_input(candidate, data, years))
    existing = session.scalar(
        select(MatchResult)
        .where(MatchResult.application_id == application.id)
        .order_by(MatchResult.computed_at.desc())
    )
    row = existing or MatchResult(application_id=application.id)
    row.overall_score = result.overall_score
    row.breakdown = match_result_to_breakdown(result)
    row.matched_skills = result.matched_skills
    row.missing_required = result.missing_required
    row.missing_preferred = result.missing_preferred
    row.extra_skills = result.extra_skills
    row.explanation = result.explanation
    row.engine_version = result.engine_version
    row.inputs_hash = result.inputs_hash
    session.add(row)
    return row


def process_document_sync(session: Session, document_id: uuid.UUID) -> None:
    """Run full CV pipeline for one document. Raises on hard failures (Celery retries)."""
    document = session.get(Document, document_id)
    if document is None:
        logger.error("process_document_missing document_id=%s", document_id)
        return

    profile = session.scalar(select(ParsedProfile).where(ParsedProfile.document_id == document_id))
    if profile is None:
        profile = ParsedProfile(document_id=document_id, candidate_id=document.candidate_id)
        session.add(profile)
        session.flush()

    profile.parse_status = ParseStatus.PROCESSING
    profile.error = None
    session.flush()

    try:
        file_bytes = storage.get_object_sync(document.storage_key)
        extracted = extract_text(file_bytes, document.mime_type or document.file_name)
        parsed = PARSER.parse(extracted.text, file_meta=extracted)
        data = parsed.to_data_dict()
        profile.raw_text = extracted.text
        profile.data = data
        profile.parser_version = parsed.parser_version
        profile.confidence = parsed.confidence
        profile.total_experience_years = (
            Decimal(str(parsed.total_experience_years))
            if parsed.total_experience_years is not None
            else None
        )

        ats = run_ats_check(extracted=extracted, parsed=parsed, mime_type=document.mime_type)
        existing_ats = session.scalar(select(AtsCheck).where(AtsCheck.document_id == document_id))
        ats_row = existing_ats or AtsCheck(document_id=document_id)
        ats_row.score = ats.score
        ats_row.checks = ats.to_checks_list()
        ats_row.engine_version = ats.engine_version
        session.add(ats_row)

        candidate = session.get(Candidate, document.candidate_id)
        if candidate is not None:
            _fill_candidate(candidate, data, parsed.total_experience_years)

        applications = session.scalars(
            select(Application).where(Application.candidate_id == document.candidate_id)
        ).all()
        for application in applications:
            score_application(session, application, profile)

        profile.parse_status = ParseStatus.DONE
        session.add(
            ActivityLog(
                candidate_id=document.candidate_id,
                application_id=document.application_id,
                action="cv.processed",
                meta={
                    "document_id": str(document_id),
                    "parser_version": parsed.parser_version,
                    "ats_score": ats.score,
                    "ocr_used": extracted.ocr_used,
                },
            )
        )
        logger.info(
            "cv_processed document_id=%s status=done ats=%s apps=%s",
            document_id,
            ats.score,
            len(applications),
        )
    except Exception as exc:
        profile.parse_status = ParseStatus.FAILED
        profile.error = type(exc).__name__
        session.add(
            ActivityLog(
                candidate_id=document.candidate_id,
                application_id=document.application_id,
                action="cv.failed",
                meta={"document_id": str(document_id), "error": type(exc).__name__},
            )
        )
        logger.exception("cv_processing_failed document_id=%s", document_id)
        raise


def rescore_job_sync(session: Session, job_id: uuid.UUID) -> int:
    apps = session.scalars(select(Application).where(Application.job_id == job_id)).all()
    count = 0
    for application in apps:
        profile = session.scalar(
            select(ParsedProfile)
            .where(
                ParsedProfile.candidate_id == application.candidate_id,
                ParsedProfile.parse_status == ParseStatus.DONE,
            )
            .order_by(ParsedProfile.created_at.desc())
        )
        if profile is None:
            continue
        score_application(session, application, profile)
        count += 1
    return count
