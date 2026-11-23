"""Remove demo data before going live. `make cleanup-demo` runs this.

Deletes every candidate, job, application, document, note, email log, notification, interview,
offer, requisition, activity and audit entry; demo users (@acme.example.com, @demo.example.com);
departments and locations outside the reference list; and every object in the CV bucket.
Keeps the organization (renamed to ORG_NAME if it still has a demo name), pipeline stages,
email templates and the reference departments.

Take a backup first (`make backup`). Refuses in production unless --force is given.
"""

import argparse
import asyncio
import sys
from typing import Any

from anyio import to_thread
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.models import (
    ActivityLog,
    Application,
    AuditLog,
    Candidate,
    ConsentRecord,
    Department,
    Document,
    EmailLog,
    Interview,
    Job,
    Location,
    Note,
    Notification,
    Offer,
    Organization,
    Requisition,
    User,
)
from app.reference_data import DEFAULT_DEPARTMENTS, ensure_org, ensure_reference_data

DEMO_USER_DOMAINS = ("@acme.example.com", "@demo.example.com")
DEMO_ORG_NAMES = ("Acme Corp",)
# Child tables first; most cascade anyway, this keeps the counts honest.
RECRUITING_TABLES: tuple[type[Any], ...] = (
    Notification,
    Note,
    EmailLog,
    Offer,
    Interview,
    ConsentRecord,
    ActivityLog,
    Document,
    Application,
    Candidate,
    Job,
    Requisition,
    AuditLog,
)


async def _count(session: AsyncSession, model: type[Any]) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def cleanup(session: AsyncSession) -> dict[str, int]:
    report: dict[str, int] = {}
    for model in RECRUITING_TABLES:
        report[model.__tablename__] = await _count(session, model)
        await session.execute(delete(model))
    # Interview children (panel, scorecards) cascade from interviews.

    demo_users = or_(*(User.email.endswith(domain) for domain in DEMO_USER_DOMAINS))
    report["demo_users"] = int(
        await session.scalar(select(func.count()).select_from(User).where(demo_users)) or 0
    )
    await session.execute(delete(User).where(demo_users))

    keep = {name.lower() for name in DEFAULT_DEPARTMENTS}
    old_departments = [
        d for d in await session.scalars(select(Department)) if d.name.lower() not in keep
    ]
    report["demo_departments"] = len(old_departments)
    for department in old_departments:
        await session.delete(department)
    report["demo_locations"] = await _count(session, Location)
    await session.execute(delete(Location))

    org = await ensure_org(session)
    if org.name in DEMO_ORG_NAMES:
        org.name = get_settings().org_name
    org.domain = None
    await ensure_reference_data(session, org)
    await session.execute(text("ALTER SEQUENCE application_reference_seq RESTART WITH 1"))
    await session.commit()
    return report


async def _run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation")
    parser.add_argument("--force", action="store_true", help="Allow when APP_ENV=production")
    parser.add_argument("--keep-files", action="store_true", help="Do not empty the CV bucket")
    args = parser.parse_args(argv)

    settings = get_settings()
    if settings.app_env == "production" and not args.force:
        print("Refusing to run with APP_ENV=production (pass --force).", file=sys.stderr)
        return 1
    if not args.yes:
        print(__doc__)
        if input("Type DELETE to continue: ").strip() != "DELETE":
            print("Cancelled.")
            return 1

    async with SessionLocal() as session:
        report = await cleanup(session)
        orgs = list(await session.scalars(select(Organization.name)))
    await engine.dispose()
    if not args.keep_files:
        report["storage_objects"] = await to_thread.run_sync(storage.delete_all_objects_sync)
    for key, value in report.items():
        print(f"  removed {value:>6}  {key}")
    print(f"Organization: {', '.join(orgs)}. Reference data ensured.")
    return 0


def main() -> int:
    return asyncio.run(_run(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
