import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cli.cleanup_demo import cleanup
from app.cli.init_admin import InitAdminError, create_or_reset
from app.cli.remove_user import RemoveUserError, remove_user
from app.core.security import verify_password
from app.models import (
    AuditLog,
    Candidate,
    Department,
    EmailTemplate,
    Job,
    PipelineStage,
    User,
)
from app.models.enums import UserRole
from app.reference_data import DEFAULT_DEPARTMENTS

STRONG = "Correct-Horse-42-battery"


async def _count(session: AsyncSession, model: type[object]) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_init_admin_creates_then_resets(db: async_sessionmaker[AsyncSession]) -> None:
    async with db() as session:
        outcome = await create_or_reset(
            session,
            email="owner@company.test",
            full_name="Owner",
            role=UserRole.SUPER_ADMIN,
            password=STRONG,
            must_change=True,
            reset=False,
        )
        assert outcome == "created"

        with pytest.raises(InitAdminError, match="already exists"):
            await create_or_reset(
                session,
                email="owner@company.test",
                full_name="Owner",
                role=UserRole.SUPER_ADMIN,
                password=STRONG,
                must_change=True,
                reset=False,
            )
        with pytest.raises(InitAdminError):
            await create_or_reset(
                session,
                email="weak@company.test",
                full_name="Weak",
                role=UserRole.HR_ADMIN,
                password="password",  # noqa: S106
                must_change=False,
                reset=False,
            )

        outcome = await create_or_reset(
            session,
            email="owner@company.test",
            full_name="Owner Renamed",
            role=UserRole.SUPER_ADMIN,
            password="Another-Strong-Pass-7",  # noqa: S106
            must_change=False,
            reset=True,
        )
        assert outcome == "reset"

    async with db() as session:
        user = await session.scalar(select(User).where(User.email == "owner@company.test"))
        assert user is not None
        assert user.must_change_password is False
        assert verify_password("Another-Strong-Pass-7", user.password_hash)


async def test_cleanup_removes_demo_data_and_keeps_reference_data(
    db: async_sessionmaker[AsyncSession],
) -> None:
    async with db() as session:
        session.add(Department(org_id=(await session.scalar(select(User.org_id))), name="Legacy"))
        await session.commit()
        assert await _count(session, Candidate) > 0
        stages_before = await _count(session, PipelineStage)

        report = await cleanup(session)

    assert report["demo_users"] == 5
    async with db() as session:
        assert await _count(session, Candidate) == 0
        assert await _count(session, Job) == 0
        assert await _count(session, User) == 0
        assert await _count(session, PipelineStage) == stages_before
        assert await _count(session, EmailTemplate) > 0
        names = set(await session.scalars(select(Department.name)))
        assert names == set(DEFAULT_DEPARTMENTS)


async def test_remove_user_deletes_account_and_audits_without_pii(
    db: async_sessionmaker[AsyncSession],
) -> None:
    async with db() as session:
        await create_or_reset(
            session,
            email="ui.review@company.test",
            full_name="UI Review",
            role=UserRole.HR_ADMIN,
            password=STRONG,
            must_change=True,
            reset=False,
        )
        role = await remove_user(session, email="UI.Review@company.test")
    assert role is UserRole.HR_ADMIN

    async with db() as session:
        gone = await session.scalar(select(User).where(User.email == "ui.review@company.test"))
        assert gone is None
        entry = await session.scalar(
            select(AuditLog).where(AuditLog.action == "user.removed_by_cli")
        )
        assert entry is not None
        assert entry.diff == {"role": "hr_admin"}
        assert "review" not in str(entry.diff).lower()
        with pytest.raises(RemoveUserError, match="No account"):
            await remove_user(session, email="ui.review@company.test")


async def test_remove_user_keeps_the_last_active_admin(
    db: async_sessionmaker[AsyncSession],
) -> None:
    async with db() as session:
        # Demo data has exactly one active super_admin.
        with pytest.raises(RemoveUserError, match="last active super_admin"):
            await remove_user(session, email="superadmin@demo.example.com")
