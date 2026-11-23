"""HR-only PDF summary and Excel export endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import AdminUser
from app.routers.applications import application_filters
from app.schemas.application import ApplicationFilters
from app.schemas.exports import PdfSummaryOptions, PdfSummaryRequest
from app.services import exports as exports_service

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.post("/pdf-summaries")
async def export_pdf_summaries(
    user: AdminUser,
    session: Session,
    body: PdfSummaryRequest,
) -> Response:
    content, media_type, filename = await exports_service.export_pdf_summaries(
        session,
        user,
        body.application_ids,
        PdfSummaryOptions(
            include_salary=body.include_salary,
            include_contact=body.include_contact,
            include_hr_notes=body.include_hr_notes,
        ),
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/excel")
async def export_excel(
    user: AdminUser,
    session: Session,
    filters: Annotated[ApplicationFilters, Depends(application_filters)],
    sort: Annotated[str | None, Query()] = None,
    application_ids: Annotated[list[UUID] | None, Query()] = None,
) -> Response:
    ids = list(application_ids) if application_ids else None
    content, filename = await exports_service.export_excel(
        session,
        user,
        filters=filters,
        sort=sort,
        application_ids=ids,
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
