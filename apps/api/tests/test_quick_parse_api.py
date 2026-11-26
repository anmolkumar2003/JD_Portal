"""POST /candidates/quick-parse: permissions, limits, nothing saved and no text in logs."""

import logging

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cv_engine.quick_fill import MAX_CHARS
from app.models import (
    ActivityLog,
    AuditLog,
    Candidate,
    CandidateDraft,
    CandidateDraftFile,
    Document,
    Note,
)
from app.services.quick_fill import QUICK_PARSE_LIMIT_PER_MINUTE
from tests.conftest import FakeRedis, login

pytestmark = pytest.mark.usefixtures("db")

URL = "/api/v1/candidates/quick-parse"
SAMPLE = (
    "Rahul Sharma, Pune, 5 years, current 8 LPA, expected 12 LPA, 30 days notice, rahul@mail.com"
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_requires_login(client: AsyncClient) -> None:
    response = await client.post(URL, json={"text": SAMPLE})

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("handle", "expected"),
    [
        ("superadmin", 200),
        ("hradmin", 200),
        ("recruiter", 403),
        ("manager", 403),
        ("interviewer", 403),
    ],
)
async def test_only_hr_admin_and_super_admin_may_use_it(
    client: AsyncClient, handle: str, expected: int
) -> None:
    token = await login(client, handle)

    response = await client.post(URL, headers=_auth(token), json={"text": SAMPLE})

    assert response.status_code == expected
    if expected == 403:
        assert response.json()["error"]["code"] == "forbidden"


async def test_response_has_the_documented_shape(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    response = await client.post(URL, headers=_auth(token), json={"text": SAMPLE})

    body = response.json()
    assert set(body) == {
        "fields",
        "warnings",
        "multiple_candidates",
        "segments",
        "ignored",
        "truncated",
    }
    for item in body["fields"]:
        assert set(item) == {
            "field",
            "value",
            "display",
            "confidence",
            "reason",
            "candidates",
            "warning",
        }
        assert item["confidence"] in {"high", "medium", "low"}


async def test_sample_sentence_returns_the_expected_values(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    response = await client.post(URL, headers=_auth(token), json={"text": SAMPLE})

    values = {item["field"]: item for item in response.json()["fields"]}
    assert values["first_name"]["value"] == "Rahul"
    assert values["last_name"]["value"] == "Sharma"
    assert values["email"]["value"] == "rahul@mail.com"
    assert values["current_location"]["value"] == "Pune"
    assert values["total_experience_years"]["value"] == 5
    assert values["notice_period_days"]["value"] == 30
    assert values["current_ctc"]["value"] == {"amount": 800000, "currency": "INR", "unit": "pa"}
    assert values["expected_ctc"]["value"] == {"amount": 1200000, "currency": "INR", "unit": "pa"}
    assert all(item["confidence"] == "high" for item in values.values())


async def test_several_candidates_are_reported_and_not_mixed(client: AsyncClient) -> None:
    token = await login(client, "hradmin")
    text = "Rahul Sharma, Pune, 5 years\nPriya Nair, Mumbai, 3 years"

    response = await client.post(URL, headers=_auth(token), json={"text": text})

    body = response.json()
    assert response.status_code == 200
    assert body["multiple_candidates"] is True
    assert body["fields"] == []
    assert len(body["segments"]) == 2
    assert body["warnings"]


async def test_ambiguous_text_returns_candidates_and_a_warning(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    response = await client.post(
        URL, headers=_auth(token), json={"text": "Rahul, Pune, 8 LPA, 12 LPA"}
    )

    ctc = next(i for i in response.json()["fields"] if i["field"] == "current_ctc")
    assert ctc["value"] is None  # nothing guessed
    assert len(ctc["candidates"]) == 2
    assert ctc["warning"]


async def test_text_exactly_at_the_limit_is_read_in_full(client: AsyncClient) -> None:
    token = await login(client, "hradmin")
    filler = ", " + "x" * (MAX_CHARS - len(SAMPLE) - 2)

    response = await client.post(URL, headers=_auth(token), json={"text": SAMPLE + filler})

    body = response.json()
    assert response.status_code == 200
    assert body["truncated"] is False  # the API refuses longer text; the engine cut is a backstop
    assert next(i for i in body["fields"] if i["field"] == "email")["value"] == "rahul@mail.com"


async def test_empty_text_is_not_an_error(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    response = await client.post(URL, headers=_auth(token), json={"text": "   \n  "})

    assert response.status_code == 200
    body = response.json()
    assert body["fields"] == []
    assert body["warnings"]


async def test_text_at_the_limit_is_accepted_and_one_over_is_refused(
    client: AsyncClient,
) -> None:
    token = await login(client, "hradmin")

    at_limit = await client.post(URL, headers=_auth(token), json={"text": "a" * MAX_CHARS})
    over = await client.post(URL, headers=_auth(token), json={"text": "b" * (MAX_CHARS + 1)})

    assert at_limit.status_code == 200
    assert over.status_code == 422
    error = over.json()["error"]
    assert error["code"] == "text_too_long"
    # The refused text is personal data: it must not come back in the error body.
    assert "b" * 50 not in over.text


async def test_missing_text_is_a_validation_error(client: AsyncClient) -> None:
    token = await login(client, "hradmin")

    response = await client.post(URL, headers=_auth(token), json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_rate_limited_per_user(client: AsyncClient, fake_redis: FakeRedis) -> None:
    token = await login(client, "hradmin")
    other = await login(client, "superadmin")

    for _ in range(QUICK_PARSE_LIMIT_PER_MINUTE):
        ok = await client.post(URL, headers=_auth(token), json={"text": "Rahul"})
        assert ok.status_code == 200
    blocked = await client.post(URL, headers=_auth(token), json={"text": "Rahul"})
    other_user = await client.post(URL, headers=_auth(other), json={"text": "Rahul"})

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert any(key.startswith("ratelimit:quick-parse:") for key in fake_redis.store)
    # The limit is per user, not shared.
    assert other_user.status_code == 200


async def _row_counts(session: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in (
        Candidate,
        CandidateDraft,
        CandidateDraftFile,
        Document,
        Note,
        ActivityLog,
        AuditLog,
    ):
        total = await session.scalar(select(func.count()).select_from(model))
        counts[model.__name__] = int(total or 0)
    return counts


async def test_nothing_is_saved(client: AsyncClient, db: async_sessionmaker[AsyncSession]) -> None:
    token = await login(client, "hradmin")
    async with db() as session:
        before = await _row_counts(session)

    for text in (SAMPLE, "x@y.com", "", "serving notice, 15 days, Bengaluru, 80k per month"):
        response = await client.post(URL, headers=_auth(token), json={"text": text})
        assert response.status_code == 200

    async with db() as session:
        after = await _row_counts(session)
    assert after == before


async def test_text_never_reaches_the_logs(
    client: AsyncClient, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    token = await login(client, "hradmin")
    marker = "zq7marker.person@leakcheck.example"
    text = f"Zephyrine Quillfeather, {marker}, +91 98765 43210, Pune, 7 years"
    caplog.set_level(logging.DEBUG)
    capsys.readouterr()  # drop the login logs

    response = await client.post(URL, headers=_auth(token), json={"text": text})

    assert response.status_code == 200
    seen = caplog.text + "".join(capsys.readouterr())
    for needle in (marker, "Zephyrine", "Quillfeather", "98765"):
        assert needle not in seen


async def test_a_failing_parse_is_reported_without_leaking_the_text(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await login(client, "hradmin")
    text_with_pii = "Zephyrine Quillfeather zq7@leakcheck.example"

    def boom(text: str) -> None:
        raise ValueError(f"could not parse {text}")

    monkeypatch.setattr("app.services.quick_fill.parse_quick_fill", boom)
    caplog.set_level(logging.DEBUG)
    capsys.readouterr()

    response = await client.post(URL, headers=_auth(token), json={"text": text_with_pii})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "quick_parse_failed"
    seen = caplog.text + "".join(capsys.readouterr()) + response.text
    assert "Zephyrine" not in seen
    assert "leakcheck" not in seen
