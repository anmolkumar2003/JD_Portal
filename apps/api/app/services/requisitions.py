"""Requisitions (REQ-01..03)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import User
from app.models.enums import EmploymentType, UserRole, WorkMode
from app.models.hiring import Requisition, RequisitionStatus
from app.schemas.job import JobCreate
from app.services.jobs import create_job


async def create_requisition(
    session: AsyncSession,
    user: User,
    *,
    title: str,
    department_id: uuid.UUID | None,
    headcount: int,
    budget_min: Decimal | None,
    budget_max: Decimal | None,
    justification: str | None,
) -> dict[str, Any]:
    req = Requisition(
        org_id=user.org_id,
        title=title,
        department_id=department_id,
        requested_by=user.id,
        headcount=headcount,
        budget_min=budget_min,
        budget_max=budget_max,
        justification=justification,
        status=RequisitionStatus.DRAFT,
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return {"id": str(req.id), "status": req.status.value}


async def submit_requisition(session: AsyncSession, user: User, req_id: uuid.UUID) -> dict[str, Any]:
    req = await session.get(Requisition, req_id)
    if req is None or req.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Requisition not found")
    req.status = RequisitionStatus.PENDING
    await session.commit()
    return {"id": str(req.id), "status": req.status.value}


async def approve_requisition(session: AsyncSession, user: User, req_id: uuid.UUID) -> dict[str, Any]:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.HIRING_MANAGER}:
        raise AppError(status.HTTP_403_FORBIDDEN, "forbidden", "Cannot approve")
    req = await session.get(Requisition, req_id)
    if req is None or req.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Requisition not found")
    req.status = RequisitionStatus.APPROVED
    req.approved_by = user.id
    req.approved_at = datetime.now(UTC)
    await session.commit()
    return {"id": str(req.id), "status": req.status.value}


async def convert_to_job(session: AsyncSession, user: User, req_id: uuid.UUID) -> dict[str, Any]:
    req = await session.get(Requisition, req_id)
    if req is None or req.org_id != user.org_id:
        raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Requisition not found")
    if req.status != RequisitionStatus.APPROVED:
        raise AppError(status.HTTP_400_BAD_REQUEST, "not_approved", "Requisition must be approved")
    job = await create_job(
        session,
        user,
        JobCreate(
            title=req.title,
            department_id=req.department_id,
            openings=req.headcount,
            description=req.justification or req.title,
            responsibilities=req.justification or "See description",
            qualifications="To be confirmed",
            work_mode=WorkMode.HYBRID,
            employment_type=EmploymentType.FULL_TIME,
        ),
    )
    return {"requisition_id": str(req.id), "job_id": str(job.id)}


async def list_requisitions(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    rows = await session.scalars(
        select(Requisition).where(Requisition.org_id == user.org_id).order_by(Requisition.created_at.desc())
    )
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "status": r.status.value,
            "headcount": r.headcount,
        }
        for r in rows
    ]
