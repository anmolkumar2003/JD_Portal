from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

FeatureFlag = Literal["public_careers", "interviews", "offers", "requisitions", "audit_ui"]


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HR Portal API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    # Fallback display name until an admin sets one in Settings > Organization.
    org_name: str = "HR Portal"
    # Browser-facing base URL of the web app, used in emailed links (password reset).
    web_base_url: str = "http://localhost:3000"

    # Optional modules, all off by default. Off means hidden in the UI and 404 from the API.
    enable_public_careers: bool = False
    enable_interviews: bool = False
    enable_offers: bool = False
    enable_requisitions: bool = False
    enable_audit_ui: bool = False

    # General per-client API rate limit (requests per minute); 0 disables it.
    api_rate_limit_per_minute: int = 300
    # Trust X-Forwarded-For (only when the API is reachable solely through our reverse proxy).
    trust_proxy_headers: bool = False

    database_url: str
    redis_url: str
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 30
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    # Set true behind HTTPS so the refresh cookie is never sent over plain HTTP.
    cookie_secure: bool = False

    s3_endpoint_url: str
    s3_public_endpoint_url: str | None = None
    s3_access_key_id: SecretStr
    s3_secret_access_key: SecretStr
    s3_bucket: str = "cvs"
    s3_region: str = "us-east-1"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = False
    smtp_from_email: str = "no-reply@hr-portal.local"
    smtp_from_name: str = "HR Portal"

    def feature_enabled(self, flag: FeatureFlag) -> bool:
        enabled: bool = getattr(self, f"enable_{flag}")
        return enabled

    @property
    def features(self) -> dict[str, bool]:
        flags: tuple[FeatureFlag, ...] = (
            "public_careers",
            "interviews",
            "offers",
            "requisitions",
            "audit_ui",
        )
        return {flag: self.feature_enabled(flag) for flag in flags}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
