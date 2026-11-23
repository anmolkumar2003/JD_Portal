"""SQLAlchemy models. Import every model module here so Alembic autogenerate can see it."""

from app.models.activity import ActivityLog
from app.models.base import Base
from app.models.candidate import Application, Candidate, Document
from app.models.comms import EmailLog, EmailTemplate, Note, Notification
from app.models.compliance import AuditLog, ConsentRecord
from app.models.cv import AtsCheck, MatchResult, ParsedProfile
from app.models.hiring import Offer, Requisition
from app.models.interviews import (
    Interview,
    InterviewPanel,
    Scorecard,
    ScorecardTemplate,
)
from app.models.job import Job, JobRequirement, JobTeam
from app.models.org_setup import Department, Location, PipelineStage
from app.models.organization import Organization
from app.models.user import User

__all__ = [
    "ActivityLog",
    "Application",
    "AtsCheck",
    "AuditLog",
    "Base",
    "Candidate",
    "ConsentRecord",
    "Department",
    "Document",
    "EmailLog",
    "EmailTemplate",
    "Interview",
    "InterviewPanel",
    "Job",
    "JobRequirement",
    "JobTeam",
    "Location",
    "MatchResult",
    "Note",
    "Notification",
    "Offer",
    "Organization",
    "ParsedProfile",
    "PipelineStage",
    "Requisition",
    "Scorecard",
    "ScorecardTemplate",
    "User",
]
