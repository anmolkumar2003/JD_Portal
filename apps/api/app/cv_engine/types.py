"""Shared types for the CV engine. No web-framework imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AtsBand = Literal["good", "needs_improvement", "poor"]


@dataclass(slots=True)
class ExtractResult:
    text: str
    ocr_used: bool = False
    page_count: int | None = None
    method: str = "unknown"
    mime_type: str | None = None
    file_size: int = 0


@dataclass(slots=True)
class ExperienceEntry:
    title: str | None = None
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    location: str | None = None


@dataclass(slots=True)
class EducationEntry:
    degree: str | None = None
    institution: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass(slots=True)
class CertificationEntry:
    name: str
    issuer: str | None = None
    date: str | None = None


@dataclass(slots=True)
class ParsedCV:
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = field(default_factory=list)
    summary: str | None = None
    skills: list[str] = field(default_factory=list)
    experience: list[ExperienceEntry] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    certifications: list[CertificationEntry] = field(default_factory=list)
    total_experience_years: float | None = None
    sections_found: list[str] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)
    parser_version: str = "rule-1.0"
    ocr_used: bool = False

    def to_data_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "links": list(self.links),
            "summary": self.summary,
            "skills": list(self.skills),
            "experience": [
                {
                    "title": e.title,
                    "company": e.company,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "description": e.description,
                    "location": e.location,
                }
                for e in self.experience
            ],
            "education": [
                {
                    "degree": e.degree,
                    "institution": e.institution,
                    "field": e.field,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                }
                for e in self.education
            ],
            "certifications": [
                {"name": c.name, "issuer": c.issuer, "date": c.date} for c in self.certifications
            ],
            "sections_found": list(self.sections_found),
        }


@dataclass(slots=True)
class AtsCheckItem:
    id: str
    label: str
    passed: bool
    weight: int
    detail: str
    suggestion: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "passed": self.passed,
            "weight": self.weight,
            "detail": self.detail,
            "suggestion": self.suggestion,
        }


@dataclass(slots=True)
class AtsResult:
    score: int
    band: AtsBand
    checks: list[AtsCheckItem]
    engine_version: str = "ats-1.0"

    def to_checks_list(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self.checks]


@dataclass(slots=True)
class SkillSpec:
    name: str
    weight: float = 1.0


@dataclass(slots=True)
class JobRequirements:
    title: str = ""
    required_skills: list[SkillSpec] = field(default_factory=list)
    preferred_skills: list[SkillSpec] = field(default_factory=list)
    min_experience: float | None = None
    max_experience: float | None = None
    education_level: str | None = None
    certifications: list[str] = field(default_factory=list)
    work_mode: str | None = None
    location_name: str | None = None
    target_notice_days: int | None = None
    weights_override: dict[str, float] | None = None
    mandatory_certifications: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CandidateMatchInput:
    skills: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    total_experience_years: float | None = None
    education_degrees: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    location: str | None = None
    notice_period_days: int | None = None


@dataclass(slots=True)
class MatchOutput:
    overall_score: int
    component_scores: dict[str, float]
    matched_skills: list[str]
    missing_required: list[str]
    missing_preferred: list[str]
    extra_skills: list[str]
    hard_filter_flags: list[str]
    explanation: dict[str, Any]
    engine_version: str = "match-1.0"
    inputs_hash: str = ""
