"""Production settings refuse weak secrets and force Secure cookies."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "app_env": "production",
        "database_url": "postgresql+asyncpg://u:p@postgres:5432/hrportal",
        "redis_url": "redis://valkey:6379/0",
        "jwt_secret": "a" * 48,
        "cors_origins": "https://portal.example.com",
        "web_base_url": "https://portal.example.com",
        "s3_endpoint_url": "http://minio:9000",
        "s3_access_key_id": "hrminio-strong-user",
        "s3_secret_access_key": "strong-minio-secret-value-32",
        "cookie_secure": False,
    }
    data.update(overrides)
    return data


def test_production_forces_cookie_secure() -> None:
    settings = Settings(**_base())  # type: ignore[arg-type]
    assert settings.cookie_secure is True


def test_production_rejects_weak_jwt() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(**_base(jwt_secret="replace-with-a-long-random-string"))  # type: ignore[arg-type]


def test_production_rejects_short_jwt() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(**_base(jwt_secret="short-but-not-placeholder"))  # type: ignore[arg-type]


def test_production_rejects_localhost_cors() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(**_base(cors_origins="https://portal.example.com,http://localhost:3000"))  # type: ignore[arg-type]


def test_development_allows_weak_placeholders() -> None:
    settings = Settings(
        **_base(  # type: ignore[arg-type]
            app_env="development",
            jwt_secret="replace-with-a-long-random-string",
            cors_origins="http://localhost:3000",
            s3_access_key_id="minioadmin",
            s3_secret_access_key="change-me-minio",
            cookie_secure=False,
        )
    )
    assert settings.cookie_secure is False
