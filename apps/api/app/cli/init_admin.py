"""Create (or reset) a portal account. `make init-admin` runs this interactively.

Run it once for the super_admin and once for the hr_admin on a fresh install. There is no
public sign-up; every other account is created from Settings > Users.

Non-interactive use (for automation):
    python -m app.cli.init_admin --email a@b.com --name "A B" --role hr_admin \
        --generate-password --password-file /run/secrets/a.txt
A generated password is never printed unless --show-password is passed; with --password-file
it is written to that file (mode 600) and the account must change it at first sign-in.
"""

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, engine
from app.core.security import generate_password, hash_password, password_problems
from app.models import User
from app.models.enums import UserRole
from app.reference_data import ensure_org, ensure_reference_data
from app.services.compliance import write_audit

ROLES = (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN, UserRole.RECRUITER)


class InitAdminError(Exception):
    pass


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email")
    parser.add_argument("--name")
    parser.add_argument("--role", choices=[r.value for r in ROLES])
    parser.add_argument("--generate-password", action="store_true")
    parser.add_argument("--password-file", type=Path)
    parser.add_argument("--show-password", action="store_true")
    parser.add_argument(
        "--reset", action="store_true", help="Reset the password if the account already exists"
    )
    return parser.parse_args(argv)


def _ask(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value


def _ask_email() -> str:
    while True:
        try:
            return validate_email(_ask("Email: "), check_deliverability=False).normalized.lower()
        except EmailNotValidError as exc:
            print(f"  {exc}")


def _ask_role() -> UserRole:
    print("Role:")
    for index, role in enumerate(ROLES, start=1):
        print(f"  {index}. {role.value}")
    while True:
        choice = _ask("Choose 1-3: ")
        if choice in {"1", "2", "3"}:
            return ROLES[int(choice) - 1]
        if choice in {r.value for r in ROLES}:
            return UserRole(choice)


def _ask_password(email: str) -> str | None:
    """Prompt for a password; an empty answer means 'generate one'."""
    while True:
        first = getpass.getpass("Password (leave empty to generate a strong one): ")
        if not first:
            return None
        problems = password_problems(first, email=email)
        if problems:
            for problem in problems:
                print(f"  {problem}")
            continue
        if getpass.getpass("Repeat password: ") != first:
            print("  Passwords do not match.")
            continue
        return first


def _write_secret(path: Path, email: str, password: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(f"{email}\t{password}\n")
    path.chmod(0o600)


async def create_or_reset(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    role: UserRole,
    password: str,
    must_change: bool,
    reset: bool,
) -> str:
    problems = password_problems(password, email=email)
    if problems:
        raise InitAdminError(" ".join(problems))
    org = await ensure_org(session)
    await ensure_reference_data(session, org)
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None and not reset:
        raise InitAdminError(
            f"{email} already exists. Re-run with --reset (or answer yes) to reset it."
        )
    action = "user.password_reset_by_cli" if user is not None else "user.created_by_cli"
    if user is None:
        user = User(org_id=org.id, email=email, full_name=full_name, role=role)
        session.add(user)
    else:
        user.full_name = full_name
        user.role = role
        user.is_active = True
        user.failed_login_attempts = 0
        user.locked_until = None
    user.password_hash = hash_password(password)
    user.must_change_password = must_change
    await session.flush()
    await write_audit(
        session,
        actor_id=None,
        action=action,
        entity_type="user",
        entity_id=user.id,
        diff={"role": role.value},
    )
    await session.commit()
    return "reset" if action.endswith("reset_by_cli") else "created"


async def _run(argv: list[str]) -> int:
    args = _parse_args(argv)
    interactive = sys.stdin.isatty() and not (args.email and args.name and args.role)

    email = (args.email or (_ask_email() if interactive else "")).lower()
    full_name = args.name or (_ask("Full name: ") if interactive else "")
    role = UserRole(args.role) if args.role else (_ask_role() if interactive else None)
    if not email or not full_name or role is None:
        print("--email, --name and --role are required when not interactive.", file=sys.stderr)
        return 2

    reset = args.reset
    async with SessionLocal() as session:
        exists = await session.scalar(select(User.id).where(User.email == email)) is not None
    if exists and not reset and interactive:
        reset = input(f"{email} exists. Reset its password? [y/N] ").strip().lower() == "y"
    if exists and not reset:
        print(f"{email} already exists; nothing changed.", file=sys.stderr)
        return 1

    typed = None if args.generate_password or not interactive else _ask_password(email)
    password = typed or generate_password()
    generated = typed is None
    if generated and not (args.password_file or args.show_password or interactive):
        print("Use --password-file or --show-password with --generate-password.", file=sys.stderr)
        return 2

    async with SessionLocal() as session:
        outcome = await create_or_reset(
            session,
            email=email,
            full_name=full_name,
            role=role,
            password=password,
            # A generated password may be seen by someone else, so it must be replaced.
            must_change=generated,
            reset=reset,
        )
    await engine.dispose()
    print(f"Account {outcome}: {email} ({role.value}).")
    if generated:
        if args.password_file:
            _write_secret(args.password_file, email, password)
            print(f"Temporary password written to {args.password_file} (mode 600).")
        if args.show_password or (interactive and not args.password_file):
            print(f"Temporary password (shown once): {password}")
        print("The password must be changed at first sign-in.")
    return 0


def main() -> int:
    try:
        return asyncio.run(_run(sys.argv[1:]))
    except InitAdminError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
