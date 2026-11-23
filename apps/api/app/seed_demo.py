"""Demo data for local development and automated tests only.

`make seed-demo` runs this and refuses unless APP_ENV=development. It is never run
automatically. The demo password comes from DEMO_PASSWORD or is generated per run and printed
once to the terminal; it is not stored anywhere.
"""

import asyncio
import hashlib
import logging
import os
import sys
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
from app.core.security import generate_password, hash_password
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
from app.reference_data import ensure_org, ensure_reference_data

logger = logging.getLogger("app.seed_demo")

M = TypeVar("M", bound=Base)

DEMO_EMAIL_DOMAIN = "demo.example.com"

DEMO_USERS: list[tuple[str, str, UserRole]] = [
    ("superadmin", "Sara Super", UserRole.SUPER_ADMIN),
    ("hradmin", "Harish Admin", UserRole.HR_ADMIN),
    ("recruiter", "Riya Recruiter", UserRole.RECRUITER),
    # Kept so record-level access (AUTH-06) stays covered by tests.
    ("manager", "Manoj Manager", UserRole.HIRING_MANAGER),
    ("interviewer", "Isha Interviewer", UserRole.INTERVIEWER),
]

ANDROID_SLUG = "senior-android-developer"
SHOPIFY_SLUG = "shopify-developer"
CONTENT_SLUG = "content-writer"

DEMO_CANDIDATE_COUNT = 30
DEMO_CANDIDATE_DOMAIN = "candidates.demo"
DEMO_CV_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
DEMO_ENGINE_VERSION = "seed-1.0"

DEMO_FIRST_NAMES = (
    "Aarav", "Ananya", "Arjun", "Bhavna", "Chirag", "Deepa", "Esha", "Farhan", "Gauri", "Harsh",
    "Ira", "Jatin", "Kavya", "Laksh", "Meera", "Nikhil", "Ojas", "Priya", "Rahul", "Saanvi",
    "Tarun", "Uma", "Varun", "Yash", "Zara", "Aditya", "Divya", "Karthik", "Neha", "Rohan",
)  # fmt: skip
DEMO_LAST_NAMES = (
    "Sharma", "Iyer", "Patel", "Menon", "Reddy", "Nair", "Gupta", "Singh", "Kulkarni", "Das",
    "Bose", "Rao", "Verma", "Pillai", "Chopra", "Joshi", "Malhotra", "Desai", "Kapoor", "Mehta",
    "Saxena", "Thakur", "Agarwal", "Banerjee", "Chatterjee", "Dubey", "Mishra", "Pandey",
    "Shetty", "Yadav",
)  # fmt: skip
# Per-candidate pipeline stage spread (must sum to DEMO_CANDIDATE_COUNT).
DEMO_STAGE_SEQUENCE: list[StageType] = (
    [StageType.APPLIED] * 6
    + [StageType.SCREENING] * 7
    + [StageType.INTERVIEW] * 6
    + [StageType.OFFER] * 3
    + [StageType.HIRED] * 2
    + [StageType.REJECTED] * 6
)

ROLE_TITLES: dict[str, tuple[str, ...]] = {
    ANDROID_SLUG: ("Android Developer", "Senior Android Engineer", "Mobile Developer"),
    SHOPIFY_SLUG: ("Shopify Developer", "Frontend Developer", "E-commerce Developer"),
}
SKILL_POOLS: dict[str, list[str]] = {
    ANDROID_SLUG: [
        "Kotlin",
        "Jetpack Compose",
        "Retrofit",
        "Android SDK",
        "Kotlin Coroutines",
        "Hilt",
        "Firebase",
        "MVVM",
    ],
    SHOPIFY_SLUG: [
        "Shopify",
        "Liquid",
        "JavaScript",
        "HTML",
        "CSS",
        "Storefront API",
        "GraphQL",
        "Shopify Themes",
    ],
}
COMPANIES = (
    "Infosys", "Wipro", "Freshworks", "Razorpay", "Flipkart", "Zoho", "Swiggy", "PhonePe",
)  # fmt: skip


def _skills(*items: tuple[str, float]) -> list[dict[str, Any]]:
    return [{"name": name, "weight": weight} for name, weight in items]


def _status_for_stage(stage: StageType) -> ApplicationStatus:
    if stage is StageType.REJECTED:
        return ApplicationStatus.REJECTED
    if stage is StageType.HIRED:
        return ApplicationStatus.HIRED
    return ApplicationStatus.ACTIVE


def _demo_profile_data(job_slug: str, *, years: Decimal, experience_index: int) -> dict[str, Any]:
    titles = ROLE_TITLES[job_slug]
    title = titles[experience_index % len(titles)]
    start_year = 2026 - int(years) - 1
    company = COMPANIES[experience_index % len(COMPANIES)]
    return {
        "skills": SKILL_POOLS[job_slug][: 5 + (experience_index % 3)],
        "summary": f"{title} with {years} years building production apps.",
        "experience": [
            {
                "company": company,
                "title": title,
                "start": f"{start_year + 2}-03",
                "end": None,
                "highlights": ["Shipped customer-facing features", "Improved app performance"],
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
    return {
        "skills": max(40, min(100, score + (score % 7) - 5)),
        "experience": max(35, min(100, score - 8)),
        "education": max(50, min(100, score + 3)),
        "title": max(45, min(100, score - 2)),
        "location": max(60, min(100, score + 5)),
    }


async def _upsert_match_result(  # noqa: PLR0913
    session: AsyncSession,
    application_id: uuid.UUID,
    *,
    overall_score: int,
    matched: list[str],
    missing_required: list[str],
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
        row = MatchResult(application_id=application_id, inputs_hash=inputs_hash)
        session.add(row)
    row.overall_score = overall_score
    row.breakdown = breakdown
    row.matched_skills = matched
    row.missing_required = missing_required
    row.missing_preferred = []
    row.extra_skills = extra
    row.explanation = {
        "summary": "Advisory match based on demo data.",
        "strengths": ["Solid overlap on core stack", "Relevant recent experience"],
        "concerns": missing_required or ["Some preferred skills not demonstrated"],
        "component_scores": breakdown,
    }
    row.engine_version = DEMO_ENGINE_VERSION
    row.inputs_hash = inputs_hash
    await session.flush()


async def _ensure_demo_cv_bundle(  # noqa: PLR0913
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    candidate: Candidate,
    application: Application,
    profile_data: dict[str, Any],
    total_years: Decimal,
    overall_score: int,
    upload_files: bool,
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
        # Only new documents get a file, so re-running never piles up storage objects.
        if upload_files:
            await storage.put_object(storage_key, DEMO_CV_BYTES, "application/pdf")

    profile = await session.scalar(
        select(ParsedProfile).where(ParsedProfile.document_id == document.id)
    )
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
        ats = AtsCheck(document_id=document.id, score=ats_score, engine_version="", checks=[])
        session.add(ats)
    ats.score = ats_score
    ats.engine_version = DEMO_ENGINE_VERSION
    ats.checks = [
        {
            "id": "A1",
            "label": "Text is extractable",
            "passed": True,
            "weight": 15,
            "detail": "Text layer found",
            "suggestion": None,
        },
        {
            "id": "A4",
            "label": "Standard section headings",
            "passed": overall_score >= 60,
            "weight": 15,
            "detail": "Experience and education sections detected",
            "suggestion": "Use conventional headings",
        },
    ]

    skills = profile_data.get("skills", [])
    missing_required: list[str] = []
    if overall_score < 70:
        pool = SKILL_POOLS[ANDROID_SLUG] if "Kotlin" in skills else SKILL_POOLS[SHOPIFY_SLUG]
        missing_required = [s for s in pool[:4] if s not in skills][:1] or [pool[3]]
    await _upsert_match_result(
        session,
        application.id,
        overall_score=overall_score,
        matched=skills[:3],
        missing_required=missing_required,
        extra=skills[3:6] if len(skills) > 3 else [],
    )


async def _seed_demo_candidates(  # noqa: PLR0913
    session: AsyncSession,
    org: Organization,
    recruiter: User,
    stages: dict[StageType, PipelineStage],
    jobs_by_slug: dict[str, Job],
    *,
    upload_files: bool,
) -> int:
    now = datetime.now(UTC)
    seeded = 0
    for index in range(DEMO_CANDIDATE_COUNT):
        first = DEMO_FIRST_NAMES[index % len(DEMO_FIRST_NAMES)]
        last = DEMO_LAST_NAMES[index % len(DEMO_LAST_NAMES)]
        email = f"demo{index + 1:02d}@{DEMO_CANDIDATE_DOMAIN}"
        job_slug = SHOPIFY_SLUG if index % 3 == 0 else ANDROID_SLUG
        job = jobs_by_slug.get(job_slug)
        if job is None or job.status is not JobStatus.OPEN:
            continue
        stage_type = DEMO_STAGE_SEQUENCE[index]
        stage = stages[stage_type]
        years = Decimal(str(3 + (index % 12)))
        titles = ROLE_TITLES[job_slug]
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
            current_title=titles[index % len(titles)],
            total_experience_years=years,
            current_ctc=Decimal(str(1_200_000 + index * 40_000)),
            expected_ctc=Decimal(str(1_800_000 + index * 45_000)),
            notice_period_days=30 if index % 4 else 60,
            linkedin_url=f"https://linkedin.com/in/{first.lower()}-{last.lower()}-{index + 1}",
            department_id=job.department_id,
            source=CandidateSource.CAREER_SITE if index % 5 else CandidateSource.REFERRAL,
            consent_given_at=now,
            consent_version="2026-01",
        )
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
            sequence = int(
                await session.scalar(select(APPLICATION_REFERENCE_SEQ.next_value())) or 0
            )
            application = Application(
                candidate_id=candidate.id,
                job_id=job.id,
                stage_id=stage.id,
                reference_no=f"APP-{now.year}-{sequence:06d}",
                status=_status_for_stage(stage_type),
                applied_at=applied_at,
                stage_entered_at=stage_entered_at,
                assigned_recruiter_id=recruiter.id,
                is_shortlisted=index % 11 == 0,
            )
            session.add(application)
            await session.flush()
        if stage_type is StageType.REJECTED:
            application.rejection_reason = (
                application.rejection_reason or "Does not meet minimum bar after screening."
            )

        await _ensure_demo_cv_bundle(
            session,
            org_id=org.id,
            candidate=candidate,
            application=application,
            profile_data=_demo_profile_data(job_slug, years=years, experience_index=index),
            total_years=years,
            overall_score=48 + (index * 17) % 53,  # 48..100 spread
            upload_files=upload_files,
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


def _job_specs(
    departments: dict[str, Department],
    location: Location,
    manager: User,
    recruiter: User,
    interviewer: User,
) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    return [
        {
            "slug": ANDROID_SLUG,
            "title": "Senior Android Developer",
            "department_id": departments["Android"].id,
            "location_id": location.id,
            "work_mode": WorkMode.HYBRID,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Senior",
            "description": "Build and scale our consumer Android apps.",
            "responsibilities": "Own features end to end, review code, mentor developers.",
            "qualifications": "5+ years building production Android apps in Kotlin.",
            "salary_min": Decimal("1800000"),
            "salary_max": Decimal("3000000"),
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
                    ("Kotlin", 1.0),
                    ("Jetpack Compose", 0.8),
                    ("Retrofit", 0.8),
                    ("Android SDK", 0.6),
                ),
                "preferred_skills": _skills(
                    ("Kotlin Coroutines", 0.5), ("Hilt", 0.4), ("Firebase", 0.4)
                ),
                "min_experience": Decimal("5"),
                "max_experience": Decimal("10"),
                "education_level": "Bachelor's",
                "certifications": [],
            },
        },
        {
            "slug": SHOPIFY_SLUG,
            "title": "Shopify Developer",
            "department_id": departments["Shopify"].id,
            "location_id": location.id,
            "work_mode": WorkMode.REMOTE,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Mid",
            "description": "Build fast, accessible Shopify storefronts for our clients.",
            "responsibilities": "Develop themes and apps, own storefront performance.",
            "qualifications": "3+ years with Shopify, Liquid and JavaScript.",
            "salary_min": Decimal("900000"),
            "salary_max": Decimal("1800000"),
            "openings": 1,
            "status": JobStatus.OPEN,
            "published_at": now,
            "hiring_manager_id": manager.id,
            "team": [(recruiter, TeamRole.RECRUITER), (manager, TeamRole.MANAGER)],
            "requirements": {
                "required_skills": _skills(
                    ("Shopify", 1.0), ("Liquid", 1.0), ("JavaScript", 0.7), ("CSS", 0.5)
                ),
                "preferred_skills": _skills(("Storefront API", 0.5), ("GraphQL", 0.4)),
                "min_experience": Decimal("3"),
                "max_experience": Decimal("7"),
                "education_level": None,
                "certifications": [],
            },
        },
        {
            "slug": CONTENT_SLUG,
            "title": "Content Writer",
            "department_id": departments["Content Writing"].id,
            "location_id": location.id,
            "work_mode": WorkMode.ONSITE,
            "employment_type": EmploymentType.FULL_TIME,
            "level": "Mid",
            "description": "Write SEO-friendly content for our clients' websites and blogs.",
            "responsibilities": "Research keywords, write and edit articles, publish in WordPress.",
            "qualifications": "2+ years of SEO content writing.",
            "salary_min": Decimal("500000"),
            "salary_max": Decimal("900000"),
            "openings": 1,
            "status": JobStatus.DRAFT,
            "published_at": None,
            "hiring_manager_id": None,
            "team": [(recruiter, TeamRole.RECRUITER)],
            "requirements": {
                "required_skills": _skills(
                    ("SEO Writing", 1.0), ("Copywriting", 0.8), ("Keyword Research", 0.6)
                ),
                "preferred_skills": _skills(("WordPress", 0.5)),
                "min_experience": Decimal("2"),
                "max_experience": None,
                "education_level": None,
                "certifications": [],
            },
        },
    ]


async def seed(session: AsyncSession, *, password: str, upload_files: bool = False) -> int:
    """Create the demo users, jobs and candidates. Returns the number of demo candidates."""
    org = await ensure_org(session)
    await ensure_reference_data(session, org)

    password_hash = hash_password(password)
    users: dict[UserRole, User] = {}
    for handle, full_name, role in DEMO_USERS:
        user = await _get_or_create(
            session,
            User,
            {"email": f"{handle}@{DEMO_EMAIL_DOMAIN}"},
            org_id=org.id,
            full_name=full_name,
            role=role,
            password_hash=password_hash,
        )
        # Re-seeding restores the demo state, including after a lockout test.
        user.role = role
        user.is_active = True
        user.must_change_password = False
        user.password_hash = password_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        users[role] = user

    departments = {
        d.name: d
        for d in await session.scalars(select(Department).where(Department.org_id == org.id))
    }
    location = await _get_or_create(
        session,
        Location,
        {"org_id": org.id, "name": "Bengaluru Office"},
        city="Bengaluru",
        country="India",
    )
    recruiter = users[UserRole.RECRUITER]
    jobs_by_slug: dict[str, Job] = {}
    for spec in _job_specs(
        departments,
        location,
        users[UserRole.HIRING_MANAGER],
        recruiter,
        users[UserRole.INTERVIEWER],
    ):
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
    count = await _seed_demo_candidates(
        session, org, recruiter, stages_by_type, jobs_by_slug, upload_files=upload_files
    )
    await session.commit()
    return count


async def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.app_env != "development":
        print(
            f"Refusing to seed demo data: APP_ENV is '{settings.app_env}', not 'development'.",
            file=sys.stderr,
        )
        return 1
    supplied = os.environ.get("DEMO_PASSWORD")
    password = supplied or generate_password()
    async with SessionLocal() as session:
        count = await seed(session, password=password, upload_files=True)
    await engine.dispose()
    print(f"Demo data ready: {len(DEMO_USERS)} users @{DEMO_EMAIL_DOMAIN}, {count} candidates.")
    if not supplied:
        print(f"Demo password for this run (shown once): {password}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
