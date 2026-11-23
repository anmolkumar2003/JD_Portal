"""Feature flags for optional modules. A disabled module answers 404, as if it did not exist."""

from collections.abc import Callable

from fastapi import status

from app.core.config import FeatureFlag, get_settings
from app.core.errors import AppError

# Path prefixes owned by optional modules. Used to map unmatched-method 405 → 404
# when the flag is off (Starlette returns 405 before route dependencies run).
DISABLED_MODULE_PREFIXES: dict[FeatureFlag, tuple[str, ...]] = {
    "public_careers": ("/api/v1/public/jobs",),
    "interviews": ("/api/v1/interviews",),
    "offers": ("/api/v1/offers",),
    "requisitions": ("/api/v1/requisitions",),
    "audit_ui": ("/api/v1/audit-logs",),
}


def feature_required(flag: FeatureFlag) -> Callable[[], None]:
    def checker() -> None:
        if not get_settings().feature_enabled(flag):
            raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Not found")

    return checker


def path_belongs_to_disabled_module(path: str) -> bool:
    """True when `path` is under an optional module whose feature flag is off."""
    settings = get_settings()
    for flag, prefixes in DISABLED_MODULE_PREFIXES.items():
        if settings.feature_enabled(flag):
            continue
        for prefix in prefixes:
            if path == prefix or path.startswith(f"{prefix}/"):
                return True
    return False
