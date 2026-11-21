from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query, status
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.errors import AppError

T = TypeVar("T")
_RowT = TypeVar("_RowT", bound=tuple[Any, ...])

SortableColumns = Mapping[str, InstrumentedAttribute[Any] | ColumnElement[Any]]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams(BaseModel):
    page: int
    page_size: int
    sort: str | None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[
        str | None, Query(description="Field name; prefix with - for descending")
    ] = None,
) -> PageParams:
    return PageParams(page=page, page_size=page_size, sort=sort)


def apply_sort(
    stmt: Select[_RowT], sort: str | None, columns: SortableColumns, default: str
) -> Select[_RowT]:
    """Order by an allow-listed column, e.g. `-created_at`. Unknown fields are rejected."""
    key = sort or default
    descending = key.startswith("-")
    name = key.lstrip("-")
    column = columns.get(name)
    if column is None:
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            "invalid_sort",
            f"Cannot sort by '{name}'",
            {"allowed": sorted(columns)},
        )
    return stmt.order_by(column.desc() if descending else column.asc())


async def paginate(
    session: AsyncSession, stmt: Select[_RowT], params: PageParams
) -> tuple[Sequence[Any], int]:
    """Return (rows, total) for a select statement. Rows are full result rows."""
    total = await session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = (await session.execute(stmt.offset(params.offset).limit(params.page_size))).all()
    return rows, total or 0
