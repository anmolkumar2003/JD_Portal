"""Quick fill: turn pasted text into suggested candidate fields.

Extract-only. The text is never saved, never put in the audit or activity log and never logged
(it is personal data). The service therefore logs only the exception *type* when something fails.
"""

import asyncio
import logging

from fastapi import status
from redis.asyncio import Redis

from app.core.errors import AppError
from app.core.rate_limit import enforce_rate_limit
from app.cv_engine.quick_fill import QuickFillResult, parse_quick_fill
from app.models import User
from app.schemas.quick_fill import (
    QUICK_PARSE_MAX_CHARS,
    QuickParseCandidateOut,
    QuickParseFieldOut,
    QuickParseOut,
)

logger = logging.getLogger(__name__)

# Per user: pasting and re-extracting is interactive, so 30 a minute is generous for a person
# and still stops a script from using the endpoint as a free parser.
QUICK_PARSE_LIMIT_PER_MINUTE = 30
QUICK_PARSE_WINDOW_SECONDS = 60


def _to_out(result: QuickFillResult) -> QuickParseOut:
    return QuickParseOut(
        fields=[
            QuickParseFieldOut(
                field=item.field,
                value=item.value,
                display=item.display,
                confidence=item.confidence,
                reason=item.reason,
                candidates=[
                    QuickParseCandidateOut(value=c.value, display=c.display, reason=c.reason)
                    for c in item.candidates
                ],
                warning=item.warning,
            )
            for item in result.fields
        ],
        warnings=result.warnings,
        multiple_candidates=result.multiple_candidates,
        segments=result.segments,
        ignored=result.ignored,
        truncated=result.truncated,
    )


async def quick_parse(redis: Redis, user: User, text: str) -> QuickParseOut:
    await enforce_rate_limit(
        redis,
        f"ratelimit:quick-parse:{user.id}",
        QUICK_PARSE_LIMIT_PER_MINUTE,
        QUICK_PARSE_WINDOW_SECONDS,
    )
    if len(text) > QUICK_PARSE_MAX_CHARS:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "text_too_long",
            f"Text is too long. The limit is {QUICK_PARSE_MAX_CHARS} characters.",
            {"max_chars": QUICK_PARSE_MAX_CHARS},
        )
    try:
        # CPU-bound (regex + spaCy), so keep it off the event loop.
        result = await asyncio.to_thread(parse_quick_fill, text)
    except Exception as exc:
        # Never log the exception message or traceback locals: they can contain the text.
        logger.error("quick parse failed", extra={"error_type": type(exc).__name__})
        raise AppError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "quick_parse_failed",
            "Could not read that text. Try fewer lines or fill the form by hand.",
        ) from None
    return _to_out(result)
