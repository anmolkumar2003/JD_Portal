from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Location, PipelineStage, User


async def list_departments(session: AsyncSession, user: User) -> Sequence[Department]:
    rows = await session.scalars(
        select(Department).where(Department.org_id == user.org_id).order_by(Department.name)
    )
    return rows.all()


async def list_locations(session: AsyncSession, user: User) -> Sequence[Location]:
    rows = await session.scalars(
        select(Location).where(Location.org_id == user.org_id).order_by(Location.name)
    )
    return rows.all()


async def list_pipeline_stages(session: AsyncSession, user: User) -> Sequence[PipelineStage]:
    rows = await session.scalars(
        select(PipelineStage)
        .where(PipelineStage.org_id == user.org_id)
        .order_by(PipelineStage.order)
    )
    return rows.all()
