"""Feature flags for optional modules. A disabled module answers 404, as if it did not exist."""

from collections.abc import Callable

from fastapi import status

from app.core.config import FeatureFlag, get_settings
from app.core.errors import AppError


def feature_required(flag: FeatureFlag) -> Callable[[], None]:
    def checker() -> None:
        if not get_settings().feature_enabled(flag):
            raise AppError(status.HTTP_404_NOT_FOUND, "not_found", "Not found")

    return checker
