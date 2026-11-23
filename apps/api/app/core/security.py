import hashlib
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

TokenType = Literal["access", "refresh", "reset"]

_hasher = PasswordHasher()

MIN_PASSWORD_LENGTH = 12
_SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"
_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password123",
        "passw0rd",
        "qwerty",
        "qwertyuiop",
        "letmein",
        "welcome",
        "admin",
        "changeme",
        "iloveyou",
        "123456789012",
    }
)


class InvalidTokenError(Exception):
    pass


def password_problems(password: str, *, email: str | None = None) -> list[str]:
    """Return the reasons a password is too weak; empty means it is acceptable."""
    problems: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"Use at least {MIN_PASSWORD_LENGTH} characters.")
    classes = sum(
        (
            any(c.islower() for c in password),
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(not c.isalnum() for c in password),
        )
    )
    if classes < 3:
        problems.append("Mix at least three of: lowercase, uppercase, numbers and symbols.")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS or any(lowered.startswith(p) for p in _COMMON_PASSWORDS):
        problems.append("Avoid common passwords.")
    local_part = (email or "").split("@", 1)[0].lower()
    if len(local_part) >= 4 and local_part in lowered:
        problems.append("Do not include your email name in the password.")
    return problems


def generate_password(length: int = 18) -> str:
    """Random password that always satisfies password_problems()."""
    alphabet = string.ascii_letters + string.digits + _SYMBOLS
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
            and any(c in _SYMBOLS for c in candidate)
            and not password_problems(candidate)
        ):
            return candidate


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_fingerprint(password_hash: str) -> str:
    """Short digest of the stored hash, so reset tokens stop working once the password changes."""
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def _encode(claims: dict[str, Any], token_type: TokenType, expires_in: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {**claims, "type": token_type, "iat": now, "exp": now + expires_in}
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> str:
    minutes = get_settings().access_token_expire_minutes
    claims = {"sub": str(user_id), "org": str(org_id), "role": role}
    return _encode(claims, "access", timedelta(minutes=minutes))


def create_refresh_token(user_id: uuid.UUID, password_hash: str) -> tuple[str, str]:
    """Return (token, jti). The jti identifies the token for logout revocation; the password
    fingerprint signs the session out everywhere once the password changes."""
    jti = uuid.uuid4().hex
    days = get_settings().refresh_token_expire_days
    claims = {"sub": str(user_id), "jti": jti, "pwd": password_fingerprint(password_hash)}
    return _encode(claims, "refresh", timedelta(days=days)), jti


def create_reset_token(user_id: uuid.UUID, password_hash: str) -> str:
    minutes = get_settings().password_reset_expire_minutes
    claims = {"sub": str(user_id), "pwd": password_fingerprint(password_hash)}
    return _encode(claims, "reset", timedelta(minutes=minutes))


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise InvalidTokenError("wrong token type")
    return payload
