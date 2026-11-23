"""LinkedIn personal-profile URL normalize + persistence."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.candidate_actions import CandidatePatch
from app.schemas.linkedin import normalize_linkedin_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://www.linkedin.com/in/username/", "https://www.linkedin.com/in/username/"),
        ("https://www.linkedin.com/in/username", "https://www.linkedin.com/in/username/"),
        ("  https://linkedin.com/in/jane-doe  ", "https://www.linkedin.com/in/jane-doe/"),
        ("linkedin.com/in/jane_doe", "https://www.linkedin.com/in/jane_doe/"),
        ("www.linkedin.com/in/a1", "https://www.linkedin.com/in/a1/"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalize_linkedin_url_accepts(raw: str | None, expected: str | None) -> None:
    assert normalize_linkedin_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.com/in/user",
        "https://www.linkedin.com/company/acme",
        "https://www.linkedin.com/pub/old-style",
        "not-a-url",
        "ftp://www.linkedin.com/in/user",
        "https://www.linkedin.com/in/",
        "https://www.linkedin.com/in/bad user",
    ],
)
def test_normalize_linkedin_url_rejects(raw: str) -> None:
    with pytest.raises(ValueError, match="LinkedIn profile URL"):
        normalize_linkedin_url(raw)


def test_candidate_patch_normalizes_linkedin() -> None:
    body = CandidatePatch.model_validate(
        {"linkedin_url": "https://linkedin.com/in/asha"}
    )
    assert body.linkedin_url == "https://www.linkedin.com/in/asha/"
    assert "linkedin_url" in body.model_fields_set


def test_candidate_patch_blank_linkedin_becomes_none() -> None:
    body = CandidatePatch.model_validate({"linkedin_url": "  "})
    assert body.linkedin_url is None
    assert "linkedin_url" in body.model_fields_set


def test_candidate_patch_rejects_non_profile() -> None:
    with pytest.raises(ValidationError):
        CandidatePatch.model_validate({"linkedin_url": "https://www.linkedin.com/company/x"})
