"""Application list filters and expanded search (location, exp, CTC, ATS, rating, skills, q)."""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    PipelineStage,
    User,
)
from app.models.candidate import APPLICATION_REFERENCE_SEQ
from app.models.enums import (
    ApplicationStatus,
    CandidateSource,
    DocumentType,
    ParseStatus,
    SalaryUnit,
    VirusScanStatus,
)
from app.schemas.application import ApplicationFilters
from app.services.applications import list_applications
from tests.conftest import login

pytestmark = pytest.mark.usefixtures("db")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _list(client: AsyncClient, token: str, **params: Any) -> tuple[int, list[dict[str, Any]]]:
    response = await client.get(
        "/api/v1/applications",
        headers=_auth(token),
        params={"page_size": 100, **params},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return int(body["total"]), list(body["items"])


async def _next_reference(session: AsyncSession) -> str:
    sequence = int(await session.scalar(select(APPLICATION_REFERENCE_SEQ.next_value())) or 0)
    return f"APP-TEST-{sequence:06d}"


async def _seed_filter_fixture(
    factory: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    """Create one tightly controlled candidate+application for filter assertions."""
    async with factory() as session:
        job = (
            await session.execute(select(Job).where(Job.slug == "senior-android-developer"))
        ).scalar_one()
        stage = (
            await session.execute(
                select(PipelineStage).where(PipelineStage.org_id == job.org_id).limit(1)
            )
        ).scalar_one()
        author_id = (
            job.created_by
            or (
                await session.execute(select(User.id).where(User.org_id == job.org_id).limit(1))
            ).scalar_one()
        )
        marker = uuid.uuid4().hex[:8]
        email = f"filter-{marker}@example.com"
        candidate = Candidate(
            org_id=job.org_id,
            first_name="Filter",
            last_name=f"Target{marker}",
            email=email,
            phone="+919876543210",
            current_location="Bengaluru Karnataka",
            current_company="Shopify Labs",
            current_title="Senior Android Engineer",
            total_experience_years=Decimal("6.5"),
            notice_period_days=45,
            expected_ctc=Decimal("1800000"),
            expected_ctc_currency="INR",
            expected_ctc_unit=SalaryUnit.PA,
            source=CandidateSource.MANUAL,
            tags=["priority", "android-hire"],
        )
        session.add(candidate)
        await session.flush()

        application = Application(
            job_id=job.id,
            candidate_id=candidate.id,
            stage_id=stage.id,
            status=ApplicationStatus.ACTIVE,
            reference_no=await _next_reference(session),
            overall_rating=Decimal("4.0"),
            is_shortlisted=True,
        )
        session.add(application)
        await session.flush()

        document = Document(
            candidate_id=candidate.id,
            application_id=application.id,
            type=DocumentType.CV,
            file_name="filter-cv.pdf",
            mime_type="application/pdf",
            size=100,
            storage_key=f"{job.org_id}/{candidate.id}/{uuid.uuid4()}.pdf",
            checksum=uuid.uuid4().hex,
            is_primary=True,
            virus_scan_status=VirusScanStatus.CLEAN,
        )
        session.add(document)
        await session.flush()

        profile = ParsedProfile(
            document_id=document.id,
            candidate_id=candidate.id,
            parse_status=ParseStatus.DONE,
            raw_text=(
                "Filter Target worked on Shopify Plus themes and Kotlin apps. "
                "Strong Python scripting for tooling."
            ),
            data={
                "skills": ["Kotlin", "Python", "Jetpack Compose"],
                "summary": "Android + tooling",
            },
            total_experience_years=Decimal("6.5"),
        )
        session.add(profile)

        session.add(
            AtsCheck(
                document_id=document.id,
                score=88,
                checks=[],
                engine_version="test",
            )
        )
        session.add(
            MatchResult(
                application_id=application.id,
                overall_score=72,
                breakdown={"skills": 70},
                matched_skills=["Kotlin"],
                missing_required=[],
                missing_preferred=[],
                extra_skills=[],
                explanation={},
                engine_version="test",
                inputs_hash=uuid.uuid4().hex,
            )
        )
        session.add(
            Note(
                candidate_id=candidate.id,
                application_id=application.id,
                author_id=author_id,
                body="Follow up about Python automation and Shopify migration.",
            )
        )
        await session.commit()
        return {
            "email": email,
            "application_id": str(application.id),
            "candidate_id": str(candidate.id),
            "last_name": candidate.last_name,
        }


@pytest.fixture
async def filter_target(
    db: async_sessionmaker[AsyncSession],
) -> dict[str, Any]:
    return await _seed_filter_fixture(db)


async def test_filter_location_alone(client: AsyncClient, filter_target: dict[str, Any]) -> None:
    token = await login(client, "recruiter")
    total, items = await _list(client, token, location="bengal")
    assert total >= 1
    assert any(i["email"] == filter_target["email"] for i in items)
    miss, _ = await _list(client, token, location="ReykjavikXYZ")
    assert miss == 0


async def test_filter_experience_range(client: AsyncClient, filter_target: dict[str, Any]) -> None:
    token = await login(client, "recruiter")
    _, items = await _list(client, token, experience_min=6, experience_max=7)
    assert any(i["email"] == filter_target["email"] for i in items)
    miss_items = (await _list(client, token, experience_min=10, experience_max=12))[1]
    assert all(i["email"] != filter_target["email"] for i in miss_items)


async def test_filter_notice_period(client: AsyncClient, filter_target: dict[str, Any]) -> None:
    token = await login(client, "recruiter")
    _, items = await _list(client, token, notice_min_days=30, notice_max_days=60)
    assert any(i["email"] == filter_target["email"] for i in items)
    _, miss_items = await _list(client, token, notice_max_days=10)
    assert all(i["email"] != filter_target["email"] for i in miss_items)


async def test_filter_expected_ctc_with_currency_unit(
    client: AsyncClient, filter_target: dict[str, Any]
) -> None:
    token = await login(client, "recruiter")
    _, items = await _list(
        client,
        token,
        expected_ctc_min=1500000,
        expected_ctc_max=2000000,
        expected_ctc_currency="INR",
        expected_ctc_unit="pa",
    )
    assert any(i["email"] == filter_target["email"] for i in items)
    miss_items = (
        await _list(
            client,
            token,
            expected_ctc_min=1500000,
            expected_ctc_currency="USD",
            expected_ctc_unit="pa",
        )
    )[1]
    assert all(i["email"] != filter_target["email"] for i in miss_items)


async def test_filter_ats_score_range(client: AsyncClient, filter_target: dict[str, Any]) -> None:
    token = await login(client, "recruiter")
    _, items = await _list(client, token, ats_score_min=80, ats_score_max=95)
    assert any(i["email"] == filter_target["email"] for i in items)
    miss_items = (await _list(client, token, ats_score_min=95, ats_score_max=100))[1]
    assert all(i["email"] != filter_target["email"] for i in miss_items)


async def test_filter_interview_rating_range(
    client: AsyncClient, filter_target: dict[str, Any]
) -> None:
    token = await login(client, "recruiter")
    _, items = await _list(client, token, rating_min=3.5, rating_max=4.5)
    assert any(i["email"] == filter_target["email"] for i in items)
    miss_items = (await _list(client, token, rating_min=4.8, rating_max=5))[1]
    assert all(i["email"] != filter_target["email"] for i in miss_items)


async def test_filter_status(client: AsyncClient, filter_target: dict[str, Any]) -> None:
    token = await login(client, "recruiter")
    _, items = await _list(client, token, status="active")
    assert any(i["email"] == filter_target["email"] for i in items)
    miss_items = (await _list(client, token, status="rejected"))[1]
    assert all(i["email"] != filter_target["email"] for i in miss_items)


async def test_filter_skills_any_and_all(
    client: AsyncClient, filter_target: dict[str, Any]
) -> None:
    token = await login(client, "recruiter")
    any_hit, any_items = await _list(
        client, token, skills=["Python", "NonexistentSkillXYZ"], skills_mode="any"
    )
    assert any(i["email"] == filter_target["email"] for i in any_items)

    all_hit, all_items = await _list(client, token, skills=["Python", "Kotlin"], skills_mode="all")
    assert any(i["email"] == filter_target["email"] for i in all_items)

    all_miss = (
        await _list(client, token, skills=["Python", "NonexistentSkillXYZ"], skills_mode="all")
    )[1]
    assert all(i["email"] != filter_target["email"] for i in all_miss)
    assert any_hit >= 1
    assert all_hit >= 1


async def test_search_q_company_title_tags_notes_cv(
    client: AsyncClient, filter_target: dict[str, Any]
) -> None:
    token = await login(client, "recruiter")
    for q in ("Shopify", "Android Engineer", "priority", "automation", "Python"):
        total, items = await _list(client, token, q=q)
        assert total >= 1, f"q={q!r} returned 0"
        assert any(i["email"] == filter_target["email"] for i in items), f"q={q!r} missed target"


async def test_filters_combined(client: AsyncClient, filter_target: dict[str, Any]) -> None:
    token = await login(client, "recruiter")
    total, items = await _list(
        client,
        token,
        location="Bengaluru",
        experience_min=5,
        experience_max=8,
        notice_max_days=60,
        expected_ctc_currency="INR",
        expected_ctc_unit="pa",
        expected_ctc_min=1000000,
        ats_score_min=80,
        rating_min=3,
        status="active",
        skills=["Kotlin"],
        skills_mode="any",
        q="Shopify",
    )
    assert total >= 1
    assert any(i["email"] == filter_target["email"] for i in items)


async def test_search_timing_1000_candidates_temp_db(
    db: async_sessionmaker[AsyncSession],
) -> None:
    """Insert 1000 candidates, time a filtered search; fixture truncates afterwards."""

    async with db() as session:
        job = (
            await session.execute(select(Job).where(Job.slug == "senior-android-developer"))
        ).scalar_one()
        stage = (
            await session.execute(
                select(PipelineStage).where(PipelineStage.org_id == job.org_id).limit(1)
            )
        ).scalar_one()
        batch: list[Candidate] = []
        for i in range(1000):
            batch.append(
                Candidate(
                    org_id=job.org_id,
                    first_name=f"Bench{i}",
                    last_name="Candidate",
                    email=f"bench{i:04d}@example.com",
                    phone=f"+9199{i:08d}",
                    current_location="Mumbai" if i % 2 == 0 else "Delhi",
                    current_company="Acme Tools" if i % 5 == 0 else "Other Co",
                    current_title="Engineer",
                    total_experience_years=Decimal(str((i % 15) + 1)),
                    notice_period_days=(i % 12) * 15,
                    expected_ctc=Decimal(str(500000 + i * 1000)),
                    expected_ctc_currency="INR",
                    expected_ctc_unit=SalaryUnit.PA,
                    source=CandidateSource.MANUAL,
                    tags=["bench", f"tag{i % 10}"],
                )
            )
        session.add_all(batch)
        await session.flush()
        apps: list[Application] = []
        for c in batch:
            apps.append(
                Application(
                    job_id=job.id,
                    candidate_id=c.id,
                    stage_id=stage.id,
                    status=ApplicationStatus.ACTIVE,
                    reference_no=await _next_reference(session),
                )
            )
        session.add_all(apps)
        await session.flush()
        for c, app in zip(batch[::50], apps[::50], strict=False):
            doc = Document(
                candidate_id=c.id,
                application_id=app.id,
                type=DocumentType.CV,
                file_name="bench.pdf",
                mime_type="application/pdf",
                size=10,
                storage_key=f"bench/{c.id}.pdf",
                checksum=uuid.uuid4().hex,
                is_primary=True,
                virus_scan_status=VirusScanStatus.CLEAN,
            )
            session.add(doc)
            await session.flush()
            session.add(
                ParsedProfile(
                    document_id=doc.id,
                    candidate_id=c.id,
                    parse_status=ParseStatus.DONE,
                    raw_text="Python Shopify tooling experience",
                    data={"skills": ["Python", "Shopify"]},
                )
            )
        await session.commit()

    async with db() as session:
        user = (
            await session.execute(select(User).where(User.email.like("recruiter@%")))
        ).scalar_one()
        filters = ApplicationFilters(
            q="Python",
            location="Mumbai",
            experience_min=2,
            experience_max=14,
            status=ApplicationStatus.ACTIVE,
            skills=["Python"],
            skills_mode="any",
        )
        params = PageParams(page=1, page_size=50, sort="-applied_at")
        started = time.perf_counter()
        items, total = await list_applications(session, user, params, filters)
        elapsed_ms = (time.perf_counter() - started) * 1000
        assert total >= 1
        assert items
        assert elapsed_ms < 2000, f"search took {elapsed_ms:.1f}ms for 1000 candidates"
