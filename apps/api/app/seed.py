"""Seed local demo data. Safe to re-run: rows are matched by natural key and reused.

Run with `make seed` (or `python -m app.seed` inside the API container).
Demo credentials are for local development only and are documented in the README.
"""

import asyncio
import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.models import (
    Application,
    AtsCheck,
    Candidate,
    Department,
    Document,
    Job,
    JobRequirement,
    JobTeam,
    Location,
    MatchResult,
    Organization,
    ParsedProfile,
    PipelineStage,
    User,
)
from app.models.base import Base
from app.models.candidate import APPLICATION_REFERENCE_SEQ
from app.models.enums import (
    ApplicationStatus,
    CandidateSource,
    DocumentType,
    EmploymentType,
    JobStatus,
    ParseStatus,
    StageType,
    TeamRole,
    UserRole,
    VirusScanStatus,
    WorkMode,
)

logger = logging.getLogger("app.seed")

M = TypeVar("M", bound=Base)

DEMO_PASSWORD = "Demo@2026!"  # noqa: S105 - local demo only, documented in README
ORG_NAME = "Acme Corp"
EMAIL_DOMAIN = "acme.example.com"

DEMO_USERS: list[tuple[str, str, UserRole]] = [
    ("superadmin", "Sara Super", UserRole.SUPER_ADMIN),
    ("hradmin", "Harish Admin", UserRole.HR_ADMIN),
    ("recruiter", "Riya Recruiter", UserRole.RECRUITER),
    ("manager", "Manoj Manager", UserRole.HIRING_MANAGER),
    ("interviewer", "Isha Interviewer", UserRole.INTERVIEWER),
]

DEFAULT_STAGES: list[tuple[str, StageType]] = [
    ("Applied", StageType.APPLIED),
    ("Screening", StageType.SCREENING),
    ("Interview", StageType.INTERVIEW),
    ("Offer", StageType.OFFER),
    ("Hired", StageType.HIRED),
    ("Rejected", StageType.REJECTED),
]

DEMO_CANDIDATE_COUNT = 30
DEMO_CANDIDATE_DOMAIN = "candidates.demo"
DEMO_CV_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
DEMO_ENGINE_VERSION = "seed-1.0"

DEMO_FIRST_NAMES = (
    "Aarav",
    "Ananya",
    "Arjun",
    "Bhavna",
    "Chirag",
    "Deepa",
    "Esha",
    "Farhan",
    "Gauri",
    "Harsh",
    "Ira",
    "Jatin",
    "Kavya",
    "Laksh",
    "Meera",
    "Nikhil",
    "Ojas",
    "Priya",
    "Rahul",
    "Saanvi",
    "Tarun",
    "Uma",
    "Varun",
    "Yash",
    "Zara",
    "Aditya",
    "Divya",
    "Karthik",
    "Neha",
    "Rohan",
)
DEMO_LAST_NAMES = (
    "Sharma",
    "Iyer",
    "Patel",
    "Menon",
    "Reddy",
    "Nair",
    "Gupta",
    "Singh",
    "Kulkarni",
    "Das",
    "Bose",
    "Rao",
    "Verma",
    "Pillai",
    "Chopra",
    "Joshi",
    "Malhotra",
    "Desai",
    "Kapoor",
    "Mehta",
    "Saxena",
    "Thakur",
    "Agarwal",
    "Banerjee",
    "Chatterjee",
    "Dubey",
    "Mishra",
    "Pandey",
    "Shetty",
    "Yadav",
)
# Per-candidate pipeline stage spread (must sum to DEMO_CANDIDATE_COUNT).
DEMO_STAGE_SEQUENCE: list[StageType] = (
    [StageType.APPLIED] * 6
    + [StageType.SCREENING] * 7
    + [StageType.INTERVIEW] * 6
    + [StageType.OFFER] * 3
    + [StageType.HIRED] * 2
    + [StageType.REJECTED] * 6
)

BACKEND_ROLE_TITLES = (
    "Backend Engineer",
    "Senior Software Engineer",
    "Platform Engineer",
    "API Developer",
    "Python Developer",
)
FRONTEND_ROLE_TITLES = (
    "Frontend Engineer",
    "UI Engineer",
    "React Developer",
    "Web Developer",
    "Product Engineer",
)
COMPANIES = (
    "Infosys",
    "Wipro",
    "Freshworks",
    "Razorpay",
    "Flipkart",
    "Zoho",
    "Swiggy",
    "PhonePe",
)


def _skills(*items: tuple[str, float]) -> list[dict[str, Any]]:
    return [{"name": name, "weight": weight} for name, weight in items]


def _status_for_stage(stage: StageType) -> ApplicationStatus:
    if stage is StageType.REJECTED:
        return ApplicationStatus.REJECTED
    if stage is StageType.HIRED:
        return ApplicationStatus.HIRED
    return ApplicationStatus.ACTIVE


def _demo_profile_data(
    job_slug: str, *, years: Decimal, experience_index: int
) -> dict[str, Any]:
    if job_slug == "frontend-engineer":
        skill_pool = ["React", "TypeScript", "Next.js", "CSS", "Tailwind CSS", "Playwright", "HTML"]
        title = FRONTEND_ROLE_TITLES[experience_index % len(FRONTEND_ROLE_TITLES)]
    else:
        skill_pool = [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Docker",
            "Kubernetes",
            "AWS",
            "Celery",
            "Redis",
        ]
        title = BACKEND_ROLE_TITLES[experience_index % len(BACKEND_ROLE_TITLES)]
    start_year = 2026 - int(years) - 1
    company = COMPANIES[experience_index % len(COMPANIES)]
    return {
        "skills": skill_pool[: 5 + (experience_index % 3)],
        "summary": f"{title} with {years} years building production systems.",
        "experience": [
            {
                "company": company,
                "title": title,
                "start": f"{start_year + 2}-03",
                "end": None,
                "highlights": ["Shipped customer-facing features", "Improved reliability and observability"],
            },
            {
                "company": COMPANIES[(experience_index + 3) % len(COMPANIES)],
                "title": f"Junior {title}",
                "start": f"{start_year}-06",
                "end": f"{start_year + 2}-02",
                "highlights": ["Worked in an agile squad", "Owned API integrations"],
            },
        ],
        "education": [
            {
                "institution": "VTU",
                "degree": "B.E. Computer Science",
                "start": "2014",
                "end": "2018",
            }
        ],
        "certifications": [],
        "links": [],
    }


def _match_breakdown(score: int) -> dict[str, int]:
    skills = max(40, min(100, score + (score % 7) - 5))
    experience = max(35, min(100, score - 8))
    education = max(50, min(100, score + 3))
    title = max(45, min(100, score - 2))
    location = max(60, min(100, score + 5))
    return {
        "skills": skills,
        "experience": experience,
        "education": education,
        "title": title,
        "location": location,
    }


async def _upsert_match_result(
    session: AsyncSession,
    application_id: uuid.UUID,
    *,
    overall_score: int,
    matched: list[str],
    missing_required: list[str],
    missing_preferred: list[str],
    extra: list[str],
) -> None:
    inputs_hash = hashlib.sha256(
        f"{application_id}:{overall_score}:{DEMO_ENGINE_VERSION}".encode()
    ).hexdigest()
    breakdown = _match_breakdown(overall_score)
    row = await session.scalar(
        select(MatchResult).where(MatchResult.application_id == application_id)
    )
    if row is None:
        row = MatchResult(
            application_id=application_id,
            overall_score=overall_score,
            breakdown=breakdown,
            matched_skills=matched,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            extra_skills=extra,
            explanation={
                "summary": "Advisory match based on seeded demo data.",
                "strengths": ["Solid overlap on core stack", "Relevant recent experience"],
                "concerns": missing_required or ["Some preferred skills not demonstrated"],
            },
            engine_version=DEMO_ENGINE_VERSION,
            inputs_hash=inputs_hash,
        )
        session.add(row)
    else:
        row.overall_score = overall_score
        row.breakdown = breakdown
        row.matched_skills = matched
        row.missing_required = missing_required
        row.missing_preferred = missing_preferred
        row.extra_skills = extra
        row.engine_version = DEMO_ENGINE_VERSION
        row.inputs_hash = inputs_hash
    await session.flush()


async def _ensure_demo_cv_bundle(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    candidate: Candidate,
    application: Application,
    profile_data: dict[str, Any],
    total_years: Decimal,
    overall_score: int,
) -> None:
    document = await session.scalar(
        select(Document).where(
            Document.application_id == application.id, Document.type == DocumentType.CV
        )
    )
    if document is None:
        document_id = uuid.uuid4()
        storage_key = f"{org_id}/{candidate.id}/{document_id}.pdf"
        document = Document(
            id=document_id,
            candidate_id=candidate.id,
            application_id=application.id,
            type=DocumentType.CV,
            file_name=f"{candidate.last_name}-CV.pdf",
            mime_type="application/pdf",
            size=len(DEMO_CV_BYTES),
            storage_key=storage_key,
            checksum=hashlib.sha256(DEMO_CV_BYTES).hexdigest(),
            is_primary=True,
            virus_scan_status=VirusScanStatus.CLEAN,
        )
        session.add(document)
        await session.flush()
        try:
            await storage.put_object(storage_key, DEMO_CV_BYTES, "application/pdf")
        except Exception:
            logger.warning(
                "demo CV not uploaded to object storage (MinIO may be down)",
                extra={"storage_key": storage_key},
            )

    profile = await session.scalar(select(ParsedProfile).where(ParsedProfile.document_id == document.id))
    if profile is None:
        profile = ParsedProfile(document_id=document.id, candidate_id=candidate.id)
        session.add(profile)
        await session.flush()
    profile.parse_status = ParseStatus.DONE
    profile.parser_version = DEMO_ENGINE_VERSION
    profile.raw_text = profile_data.get("summary")
    profile.data = profile_data
    profile.total_experience_years = total_years
    profile.confidence = {"skills": 0.9, "experience": 0.85, "education": 0.8}

    ats = await session.scalar(select(AtsCheck).where(AtsCheck.document_id == document.id))
    ats_score = 65 + (overall_score % 30)
    if ats is None:
        ats = AtsCheck(
            document_id=document.id,
            score=ats_score,
            checks=[
                {
                    "id": "fonts",
                    "label": "Standard fonts",
                    "passed": True,
                    "weight": 10,
                    "detail": "Uses common fonts",
                    "suggestion": None,
                },
                {
                    "id": "sections",
                    "label": "Clear sections",
                    "passed": overall_score >= 60,
                    "weight": 15,
                    "detail": "Experience and education sections detected",
                    "suggestion": None,
                },
            ],
            engine_version=DEMO_ENGINE_VERSION,
        )
        session.add(ats)
    else:
        ats.score = ats_score
        ats.engine_version = DEMO_ENGINE_VERSION

    skills = profile_data.get("skills", [])
    matched = skills[:3]
    missing_required: list[str] = []
    missing_preferred: list[str] = []
    extra = skills[3:6] if len(skills) > 3 else []
    if overall_score < 70:
        missing_required = ["Kubernetes"] if "kubernetes" not in {s.lower() for s in skills} else []
    await _upsert_match_result(
        session,
        application.id,
        overall_score=overall_score,
        matched=matched,
        missing_required=missing_required,
        missing_preferred=missing_preferred,
        extra=extra,
    )


async def _seed_demo_candidates(
    session: AsyncSession,
    org: Organization,
    recruiter: User,
    stages: dict[StageType, PipelineStage],
    jobs_by_slug: dict[str, Job],
) -> int:
    now = datetime.now(UTC)
    seeded = 0
    for index in range(DEMO_CANDIDATE_COUNT):
        first = DEMO_FIRST_NAMES[index % len(DEMO_FIRST_NAMES)]
        last = DEMO_LAST_NAMES[index % len(DEMO_LAST_NAMES)]
        email = f"demo{index + 1:02d}@{DEMO_CANDIDATE_DOMAIN}"
        job_slug = "frontend-engineer" if index % 3 == 0 else "senior-backend-engineer"
        job = jobs_by_slug.get(job_slug)
        if job is None or job.status is not JobStatus.OPEN:
            continue
        stage_type = DEMO_STAGE_SEQUENCE[index]
        stage = stages[stage_type]
        years = Decimal(str(3 + (index % 12)))
        title_pool = FRONTEND_ROLE_TITLES if job_slug == "frontend-engineer" else BACKEND_ROLE_TITLES
        company = COMPANIES[index % len(COMPANIES)]

        candidate = await _get_or_create(
            session,
            Candidate,
            {"org_id": org.id, "email": email},
            first_name=first,
            last_name=last,
            phone=f"+91 98{index:03d} 4{index:04d}",
            current_location="Bengaluru" if index % 2 == 0 else "Remote, India",
            current_company=company,
            current_title=title_pool[index % len(title_pool)],
            total_experience_years=years,
            expected_ctc=Decimal(str(1_800_000 + index * 45_000)),
            notice_period_days=30 if index % 4 else 60,
            linkedin_url=f"https://linkedin.com/in/{first.lower()}-{last.lower()}-{index + 1}",
            source=CandidateSource.CAREER_SITE if index % 5 else CandidateSource.REFERRAL,
            consent_given_at=now,
            consent_version="2026-01",
        )
        candidate.total_experience_years = years
        candidate.current_title = title_pool[index % len(title_pool)]
        if index % 7 == 0:
            candidate.tags = ["silver-medalist"]

        application = await session.scalar(
            select(Application).where(
                Application.candidate_id == candidate.id, Application.job_id == job.id
            )
        )
        days_ago = 3 + (index % 45)
        applied_at = now - timedelta(days=days_ago)
        stage_entered_at = applied_at + timedelta(days=index % 12)
        if application is None:
            sequence = int(await session.scalar(select(APPLICATION_REFERENCE_SEQ.next_value())) or 0)
            reference_no = f"APP-{now.year}-{sequence:06d}"
            application = Application(
                candidate_id=candidate.id,
                job_id=job.id,
                stage_id=stage.id,
                reference_no=reference_no,
                status=_status_for_stage(stage_type),
                applied_at=applied_at,
                stage_entered_at=stage_entered_at,
                assigned_recruiter_id=recruiter.id,
                is_shortlisted=index % 11 == 0,
            )
            session.add(application)
            await session.flush()
        else:
            application.stage_id = stage.id
            application.status = _status_for_stage(stage_type)
            application.stage_entered_at = stage_entered_at
            application.assigned_recruiter_id = recruiter.id
            application.is_shortlisted = index % 11 == 0

        if stage_type is StageType.REJECTED:
            application.rejection_reason = (
                application.rejection_reason or "Does not meet minimum bar after screening."
            )
        elif application.rejection_reason and stage_type is not StageType.REJECTED:
            application.rejection_reason = None

        profile_data = _demo_profile_data(job_slug, years=years, experience_index=index)
        overall_score = 48 + (index * 17) % 53  # 48..100 spread
        await _ensure_demo_cv_bundle(
            session,
            org_id=org.id,
            candidate=candidate,
            application=application,
            profile_data=profile_data,
            total_years=years,
            overall_score=overall_score,
        )
        seeded += 1

    return seeded


async def _get_or_create(
    session: AsyncSession, model: type[M], lookup: dict[str, Any], **values: Any
) -> M:
    instance = await session.scalar(select(model).filter_by(**lookup))
    if instance is None:
        instance = model(**lookup, **values)
        session.add(instance)
        await session.flush()
    return instance


async def seed(session: AsyncSession) -> int:
    org = await _get_or_create(
        session, Organization, {"name": ORG_NAME}, domain=EMAIL_DOMAIN, settings={}
    )

    password_hash = hash_password(DEMO_PASSWORD)
    users: dict[UserRole, User] = {}
    for handle, full_name, role in DEMO_USERS:
        user = await _get_or_create(
            session,
            User,
            {"email": f"{handle}@{EMAIL_DOMAIN}"},
            org_id=org.id,
            full_name=full_name,
            role=role,
            password_hash=password_hash,
        )
        # Re-seeding restores the documented demo state, including after a lockout test.
        user.role = role
        user.is_active = True
        user.password_hash = password_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        users[role] = user

    for order, (name, stage_type) in enumerate(DEFAULT_STAGES, start=1):
        await _get_or_create(
            session,
            PipelineStage,
            {"org_id": org.id, "name": name},
            order=order,
            type=stage_type,
            is_default=True,
        )

    manager = users[UserRole.HIRING_MANAGER]
    engineering = await _get_or_create(
        session, Department, {"org_id": org.id, "name": "Engineering"}, head_user_id=manager.id
    )
    people = await _get_or_create(
        session, Department, {"org_id": org.id, "name": "People Operations"}
    )
    bengaluru = await _get_or_create(
        session,
        Location,
        {"org_id": org.id, "name": "Bengaluru HQ"},
        city="Bengaluru",
        country="India",
    )
    remote = await _get_or_create(
        session, Location, {"org_id": org.id, "name": "Remote (India)"}, country="India"
    )

    now = datetime.now(UTC)
    recruiter = users[UserRole.RECRUITER]
    interviewer = users[UserRole.INTERVIEWER]
    jobs: list[dict[str, Any]] = [
        {
            "slug": "senior-backend-engineer",
            "title": "Senior Backend Engineer",
            "department_id": engineering.id,
            "location_id": bengaluru.id,
            "work_mode": WorkMode.HYBRID,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Senior",
            "description": "Build and scale the APIs behind our recruitment platform.",
            "responsibilities": "Design services, own reliability, mentor engineers.",
            "qualifications": "5+ years building production backend systems.",
            "salary_min": Decimal("2500000"),
            "salary_max": Decimal("4000000"),
            "openings": 2,
            "status": JobStatus.OPEN,
            "published_at": now,
            "hiring_manager_id": manager.id,
            "team": [
                (recruiter, TeamRole.RECRUITER),
                (manager, TeamRole.MANAGER),
                (interviewer, TeamRole.INTERVIEWER),
            ],
            "requirements": {
                "required_skills": _skills(
                    ("Python", 1.0), ("FastAPI", 0.8), ("PostgreSQL", 0.8), ("Docker", 0.6)
                ),
                "preferred_skills": _skills(("Kubernetes", 0.5), ("Celery", 0.4), ("AWS", 0.4)),
                "min_experience": Decimal("5"),
                "max_experience": Decimal("10"),
                "education_level": "Bachelor's",
                "certifications": [],
            },
        },
        {
            "slug": "frontend-engineer",
            "title": "Frontend Engineer",
            "department_id": engineering.id,
            "location_id": remote.id,
            "work_mode": WorkMode.REMOTE,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Mid",
            "description": "Craft fast, accessible interfaces for recruiters and candidates.",
            "responsibilities": "Build React features, own UI quality and accessibility.",
            "qualifications": "3+ years with React and TypeScript.",
            "salary_min": Decimal("1500000"),
            "salary_max": Decimal("2800000"),
            "openings": 1,
            "status": JobStatus.OPEN,
            "published_at": now,
            "hiring_manager_id": manager.id,
            "team": [(recruiter, TeamRole.RECRUITER), (manager, TeamRole.MANAGER)],
            "requirements": {
                "required_skills": _skills(
                    ("React", 1.0), ("TypeScript", 1.0), ("Next.js", 0.7), ("CSS", 0.5)
                ),
                "preferred_skills": _skills(("Tailwind CSS", 0.5), ("Playwright", 0.4)),
                "min_experience": Decimal("3"),
                "max_experience": Decimal("7"),
                "education_level": None,
                "certifications": [],
            },
        },
        {
            "slug": "hr-business-partner",
            "title": "HR Business Partner",
            "department_id": people.id,
            "location_id": bengaluru.id,
            "work_mode": WorkMode.ONSITE,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Senior",
            "description": "Partner with leaders on talent, performance and culture.",
            "responsibilities": "Advise managers, run talent reviews, drive engagement.",
            "qualifications": "6+ years in HR business partnering.",
            "salary_min": Decimal("1800000"),
            "salary_max": Decimal("3000000"),
            "openings": 1,
            "status": JobStatus.DRAFT,
            "published_at": None,
            "hiring_manager_id": None,
            "team": [(recruiter, TeamRole.RECRUITER)],
            "requirements": {
                "required_skills": _skills(
                    ("Employee Relations", 1.0), ("Talent Management", 0.8), ("HR Analytics", 0.6)
                ),
                "preferred_skills": _skills(("SHRM-CP", 0.5), ("Workday", 0.4)),
                "min_experience": Decimal("6"),
                "max_experience": None,
                "education_level": "Master's",
                "certifications": ["SHRM-CP"],
            },
        },
    ]

    jobs_by_slug: dict[str, Job] = {}
    for spec in jobs:
        team = spec.pop("team")
        requirements = spec.pop("requirements")
        slug = spec.pop("slug")
        job = await _get_or_create(
            session,
            Job,
            {"slug": slug},
            org_id=org.id,
            created_by=recruiter.id,
            salary_currency="INR",
            **spec,
        )
        jobs_by_slug[slug] = job
        await _get_or_create(session, JobRequirement, {"job_id": job.id}, **requirements)
        for member, team_role in team:
            await _get_or_create(
                session, JobTeam, {"job_id": job.id, "user_id": member.id, "team_role": team_role}
            )

    stage_rows = await session.scalars(select(PipelineStage).where(PipelineStage.org_id == org.id))
    stages_by_type = {row.type: row for row in stage_rows}
    demo_candidates = await _seed_demo_candidates(
        session, org, recruiter, stages_by_type, jobs_by_slug
    )

    await session.commit()
    return demo_candidates


async def main() -> None:
    configure_logging(get_settings().log_level)
    async with SessionLocal() as session:
        demo_candidates = await seed(session)
    await engine.dispose()
    logger.info(
        "seed complete",
        extra={
            "org": ORG_NAME,
            "users": len(DEMO_USERS),
            "stages": len(DEFAULT_STAGES),
            "jobs": 3,
            "demo_candidates": demo_candidates,
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
