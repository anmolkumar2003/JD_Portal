from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.services import analytics as analytics_service
from app.services import search as search_service

router = APIRouter(prefix="/api/v1", tags=["analytics"])
Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/analytics/overview")
async def overview(
    user: CurrentUser,
    session: Session,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    return await analytics_service.overview(session, user, start=start, end=end)


@router.get("/analytics/funnel")
async def funnel(user: CurrentUser, session: Session) -> list[dict[str, Any]]:
    return await analytics_service.funnel(session, user)


@router.get("/analytics/sources")
async def sources(user: CurrentUser, session: Session) -> list[dict[str, Any]]:
    return await analytics_service.sources(session, user)


@router.get("/analytics/applications-over-time")
async def over_time(
    user: CurrentUser,
    session: Session,
    days: Annotated[int, Query(ge=7, le=365)] = 30,
) -> list[dict[str, Any]]:
    return await analytics_service.applications_over_time(session, user, days=days)


@router.get("/analytics/export")
async def export_csv(user: CurrentUser, session: Session) -> Response:
    content = await analytics_service.export_csv(session, user)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )


@router.get("/search")
async def search(
    user: CurrentUser,
    session: Session,
    q: Annotated[str, Query(min_length=1, max_length=200)],
) -> dict[str, list[dict[str, Any]]]:
    return await search_service.global_search(session, user, q)
