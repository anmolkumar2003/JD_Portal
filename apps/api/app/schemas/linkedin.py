"""LinkedIn personal-profile URL normalize + validate."""

from __future__ import annotations

from urllib.parse import urlparse

_MSG = "Enter a LinkedIn profile URL like https://www.linkedin.com/in/username"


def normalize_linkedin_url(value: str | None) -> str | None:
    """Trim, optional https:// prefix, require linkedin.com /in/{username}."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    candidate = raw
    lower = candidate.lower()
    if not lower.startswith(("http://", "https://")):
        if lower.startswith("linkedin.com/") or lower.startswith("www.linkedin.com/"):
            candidate = f"https://{candidate}"
        else:
            raise ValueError(_MSG)

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(_MSG)

    host = (parsed.hostname or "").lower()
    if host not in ("linkedin.com", "www.linkedin.com"):
        raise ValueError(_MSG)

    parts = [p for p in (parsed.path or "").split("/") if p]
    if len(parts) < 2 or parts[0].lower() != "in":
        raise ValueError(_MSG)

    username = parts[1]
    if not username or not all(c.isalnum() or c in "-_" for c in username):
        raise ValueError(_MSG)

    # Canonical form: https + www + /in/{user}/ (trailing slash, no query/fragment noise)
    return f"https://www.linkedin.com/in/{username}/"
