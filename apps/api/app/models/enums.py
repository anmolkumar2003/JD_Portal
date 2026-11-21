import enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=enum.Enum)


class UserRole(enum.StrEnum):
    SUPER_ADMIN = "super_admin"
    HR_ADMIN = "hr_admin"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"


class WorkMode(enum.StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class EmploymentType(enum.StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class JobStatus(enum.StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    FILLED = "filled"


class TeamRole(enum.StrEnum):
    RECRUITER = "recruiter"
    INTERVIEWER = "interviewer"
    MANAGER = "manager"


class StageType(enum.StrEnum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    CUSTOM = "custom"


class CandidateSource(enum.StrEnum):
    CAREER_SITE = "career_site"
    REFERRAL = "referral"
    LINKEDIN = "linkedin"
    AGENCY = "agency"
    MANUAL = "manual"


class ApplicationStatus(enum.StrEnum):
    ACTIVE = "active"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    HIRED = "hired"


class DocumentType(enum.StrEnum):
    CV = "cv"
    COVER_LETTER = "cover_letter"
    OFFER = "offer"
    OTHER = "other"


class VirusScanStatus(enum.StrEnum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    FAILED = "failed"


class ParseStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


def pg_enum(enum_cls: type[E], name: str) -> SAEnum:
    """Postgres enum that stores the lowercase values rather than the member names."""
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda cls: [member.value for member in cls],
    )
