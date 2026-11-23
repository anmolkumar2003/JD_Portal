"""Reference data every installation needs: pipeline stages, email templates and departments.

Idempotent: existing rows (including admin edits and deactivations) are left untouched, only
missing rows are added. Contains no people, candidates or jobs.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Department, EmailTemplate, Organization, PipelineStage
from app.models.enums import StageType

DEFAULT_STAGES: tuple[tuple[str, StageType], ...] = (
    ("Applied", StageType.APPLIED),
    ("Screening", StageType.SCREENING),
    ("Interview", StageType.INTERVIEW),
    ("Offer", StageType.OFFER),
    ("Hired", StageType.HIRED),
    ("Rejected", StageType.REJECTED),
)

DEFAULT_DEPARTMENTS: tuple[str, ...] = (
    "Content Writing",
    "Shopify",
    "PPC",
    "Android",
    "iOS",
    "Flutter",
    "Quality Analyst",
    "UX Design",
    "Project Manager",
)

TEMPLATE_VARIABLES = ["candidate_name", "first_name", "job_title", "org_name", "reference_no"]

# (key, subject, body). Bodies are plain text with {{variables}}; none is linked to a stage,
# so nothing is ever sent automatically.
DEFAULT_EMAIL_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    (
        "application_received",
        "We received your application for {{job_title}}",
        "Hi {{first_name}},\n\nThank you for your interest in the {{job_title}} role at "
        "{{org_name}}. We have received your details and our team will review them shortly.\n\n"
        "Best regards,\n{{org_name}} HR",
    ),
    (
        "interview_invitation",
        "Interview invitation: {{job_title}} at {{org_name}}",
        "Hi {{first_name}},\n\nWe would like to invite you to an interview for the "
        "{{job_title}} role. Please reply with a few time slots that suit you this week.\n\n"
        "Best regards,\n{{org_name}} HR",
    ),
    (
        "rejection",
        "Your application for {{job_title}}",
        "Hi {{first_name}},\n\nThank you for the time you invested in applying for the "
        "{{job_title}} role at {{org_name}}. After careful consideration we will not be moving "
        "forward with your application at this time. We will keep your profile on file for "
        "future openings.\n\nBest wishes,\n{{org_name}} HR",
    ),
    (
        "offer_discussion",
        "Next steps for {{job_title}}",
        "Hi {{first_name}},\n\nWe enjoyed getting to know you and would like to discuss an "
        "offer for the {{job_title}} role. When would be a good time for a call?\n\n"
        "Best regards,\n{{org_name}} HR",
    ),
    (
        "follow_up",
        "Following up on your application",
        "Hi {{first_name}},\n\nI wanted to follow up regarding your application for "
        "{{job_title}}. Could you share your availability and current notice period?\n\n"
        "Best regards,\n{{org_name}} HR",
    ),
)


@dataclass(frozen=True)
class ReferenceDataResult:
    stages_added: int
    templates_added: int
    departments_added: int


async def ensure_org(session: AsyncSession) -> Organization:
    """Return the company organization, creating it from ORG_NAME on a fresh install."""
    org = await session.scalar(select(Organization).order_by(Organization.created_at).limit(1))
    if org is None:
        org = Organization(name=get_settings().org_name, settings={})
        session.add(org)
        await session.flush()
    return org


async def ensure_reference_data(session: AsyncSession, org: Organization) -> ReferenceDataResult:
    stage_names = set(
        await session.scalars(select(PipelineStage.name).where(PipelineStage.org_id == org.id))
    )
    stage_orders = set(
        await session.scalars(select(PipelineStage.order).where(PipelineStage.org_id == org.id))
    )
    stages_added = 0
    next_order = max(stage_orders, default=0) + 1
    for order, (name, stage_type) in enumerate(DEFAULT_STAGES, start=1):
        if name in stage_names:
            continue
        slot = order if order not in stage_orders else next_order
        stage_orders.add(slot)
        next_order = max(stage_orders) + 1
        session.add(
            PipelineStage(org_id=org.id, name=name, order=slot, type=stage_type, is_default=True)
        )
        stages_added += 1

    template_keys = set(
        await session.scalars(select(EmailTemplate.key).where(EmailTemplate.org_id == org.id))
    )
    templates_added = 0
    for key, subject, body in DEFAULT_EMAIL_TEMPLATES:
        if key in template_keys:
            continue
        session.add(
            EmailTemplate(
                org_id=org.id,
                key=key,
                subject=subject,
                body_html=body,
                variables=TEMPLATE_VARIABLES,
                is_active=True,
            )
        )
        templates_added += 1

    department_names = {
        name.lower()
        for name in await session.scalars(
            select(Department.name).where(Department.org_id == org.id)
        )
    }
    departments_added = 0
    for name in DEFAULT_DEPARTMENTS:
        if name.lower() not in department_names:
            session.add(Department(org_id=org.id, name=name))
            departments_added += 1

    await session.flush()
    return ReferenceDataResult(stages_added, templates_added, departments_added)
