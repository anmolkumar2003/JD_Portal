"""Permanently remove a portal account. `make remove-user EMAIL=a@b.com` runs this.

Use it to retire an account that should not exist at all (for example a review or test login).
Rows that point at the user (audit trail, notes, activity) keep existing with the author cleared;
nothing about candidates changes. The audit entry stores the user id and role only, never the
name or email.

Guards: the last active super_admin and the last active hr_admin can never be removed.
"""

import argparse
import asyncio
import sys

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, engine
from app.models import User
from app.models.enums import UserRole
from app.services.compliance import write_audit

PROTECTED_ROLES = (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN)


class RemoveUserError(Exception):
    pass


async def remove_user(session: AsyncSession, *, email: str) -> UserRole:
    user = await session.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise RemoveUserError("No account with that email.")
    if user.role in PROTECTED_ROLES and user.is_active:
        others = int(
            await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == user.role, User.is_active.is_(True), User.id != user.id)
            )
            or 0
        )
        if others == 0:
            raise RemoveUserError(f"Refusing to remove the last active {user.role.value}.")
    role, user_id = user.role, user.id
    await session.delete(user)
    await session.flush()
    await write_audit(
        session,
        actor_id=None,
        action="user.removed_by_cli",
        entity_type="user",
        entity_id=user_id,
        diff={"role": role.value},
    )
    await session.commit()
    return role


async def _run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation")
    args = parser.parse_args(argv)
    if not args.yes:
        answer = input(f"Permanently remove {args.email}? This cannot be undone. [y/N] ")
        if answer.strip().lower() != "y":
            print("Cancelled.", file=sys.stderr)
            return 1
    try:
        async with SessionLocal() as session:
            role = await remove_user(session, email=args.email)
    except RemoveUserError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        await engine.dispose()
    print(f"Removed {args.email} ({role.value}).")
    return 0


def main() -> int:
    try:
        return asyncio.run(_run(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
