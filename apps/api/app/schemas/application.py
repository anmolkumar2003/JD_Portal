from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=6, max_length=40, pattern=r"^\+?[0-9 ()\-.]+$"
    ),
]


class ApplyForm(BaseModel):
    """Multipart text fields of the public apply form (APPLY-02/03)."""

    first_name: Name
    last_name: Name
    email: EmailStr
    phone: Phone
    current_location: ShortText | None = None
    current_company: ShortText | None = None
    current_title: ShortText | None = None
    total_experience_years: Annotated[Decimal, Field(ge=0, le=50, decimal_places=1)] | None = None
    expected_ctc: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)] | None = None
    notice_period_days: Annotated[int, Field(ge=0, le=365)] | None = None
    linkedin_url: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None
    cover_letter: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] | None
    ) = None
    consent: bool
    # Honeypot: hidden from people, so any value means a bot filled the form.
    website: str = ""

    @model_validator(mode="before")
    @classmethod
    def _blank_to_none(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: (None if isinstance(v, str) and not v.strip() and k != "website" else v)
                for k, v in data.items()
            }
        return data

    @field_validator("linkedin_url")
    @classmethod
    def _check_url(cls, value: str | None) -> str | None:
        if value is not None and not value.lower().startswith(("https://", "http://")):
            raise ValueError("Must be a full URL starting with https://")
        return value

    @field_validator("consent")
    @classmethod
    def _require_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent is required to apply")
        return value


class ApplyResult(BaseModel):
    reference_no: str
    job_title: str


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int
    file_name: str
