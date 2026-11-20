from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.schemas.org import DepartmentOut, LocationOut, PipelineStageOut
from app.services import org as org_service

router = APIRouter(prefix="/api/v1", tags=["org"])

Session = Annotated[AsyncSession, Depends(get_db)]


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(user: CurrentUser, session: Session) -> list[DepartmentOut]:
    rows = await org_service.list_departments(session, user)
    return [DepartmentOut.model_validate(d) for d in rows]


@router.get("/locations", response_model=list[LocationOut])
async def list_locations(user: CurrentUser, session: Session) -> list[LocationOut]:
    rows = await org_service.list_locations(session, user)
    return [LocationOut.model_validate(loc) for loc in rows]


@router.get("/pipeline-stages", response_model=list[PipelineStageOut])
async def list_pipeline_stages(user: CurrentUser, session: Session) -> list[PipelineStageOut]:
    rows = await org_service.list_pipeline_stages(session, user)
    return [PipelineStageOut.model_validate(stage) for stage in rows]
