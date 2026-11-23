"""Simple interview ratings and advisory final score."""

from datetime import datetime
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.interviews import Recommendation

RoundName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Mode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class SkillRatingIn(BaseModel):
    skill: SkillName
    rating: Annotated[int, Field(ge=1, le=5)] | None = None  # None = not assessed


class InterviewRatingIn(BaseModel):
    round_name: RoundName
    interviewed_at: datetime
    interviewer_name: PersonName
    interviewer_id: UUID | None = None
    mode: Mode = "video"
    comments: LongText | None = None
    skill_ratings: list[SkillRatingIn] = Field(default_factory=list, max_length=40)
    overall_rating: Annotated[int, Field(ge=1, le=5)]
    recommendation: Recommendation
    strengths: LongText | None = None
    concerns: LongText | None = None


class InterviewRatingOut(BaseModel):
    id: UUID
    application_id: UUID
    round_name: str
    interviewed_at: datetime
    interviewer_name: str
    interviewer_id: UUID | None
    mode: str
    comments: str | None
    skill_ratings: list[dict[str, Any]]
    overall_rating: int
    recommendation: Recommendation
    strengths: str | None
    concerns: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class ScoringWeights(BaseModel):
    """Percent weights for the advisory final score. Must sum to 100."""

    match_weight: Annotated[int, Field(ge=0, le=100)] = 50
    interview_weight: Annotated[int, Field(ge=0, le=100)] = 50

    @model_validator(mode="after")
    def _sum_100(self) -> Self:
        if self.match_weight + self.interview_weight != 100:
            raise ValueError("match_weight and interview_weight must sum to 100")
        return self


class FinalScoreOut(BaseModel):
    """Advisory composite. Never used to auto-reject or auto-advance."""

    match_score: int | None
    ats_score: int | None
    interview_avg: float | None
    weights: ScoringWeights
    final_score: float | None
    note: str = "Advisory only. Scores never auto-reject or auto-advance a candidate."
