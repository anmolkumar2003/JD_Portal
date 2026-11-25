"""Request/response schemas for permanent candidate deletion."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

MAX_BULK_DELETE = 100


class CandidateDeleteOut(BaseModel):
    """`counts` holds row counts per table plus storage outcome; never any candidate data."""

    id: UUID
    deleted: bool = True
    counts: dict[str, int]


class BulkCandidateDeleteRequest(BaseModel):
    candidate_ids: list[UUID] = Field(min_length=1, max_length=MAX_BULK_DELETE)


class CandidateDeleteFailure(BaseModel):
    id: UUID
    code: str
    message: str


class BulkCandidateDeleteOut(BaseModel):
    deleted: list[CandidateDeleteOut]
    failed: list[CandidateDeleteFailure]
