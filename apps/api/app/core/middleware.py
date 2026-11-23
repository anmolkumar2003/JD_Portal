import json
import logging
import re
import time
from uuid import uuid4

from redis.exceptions import RedisError
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.net import client_ip
from app.core.rate_limit import resolve
from app.core.redis import redis_client
from app.core.request_context import request_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"
# Caller-supplied ids are echoed into logs, so only accept a safe charset.
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")

logger = logging.getLogger("app.request")


class RequestIDMiddleware:
    """Assign a request id, expose it in a response header and log one line per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = incoming if incoming and _VALID_REQUEST_ID.fullmatch(incoming) else uuid4().hex
        token = request_id_ctx.set(request_id)
        status_code = 500
        start = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                },
            )
            request_id_ctx.reset(token)


class RateLimitMiddleware:
    """Fixed one-minute window per client IP across the API. Fails open if Redis is down."""

    _EXEMPT_PREFIXES = ("/health", "/docs", "/openapi.json")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = get_settings().api_rate_limit_per_minute
        if (
            scope["type"] != "http"
            or limit <= 0
            or scope["method"] == "OPTIONS"
            or scope["path"].startswith(self._EXEMPT_PREFIXES)
        ):
            await self.app(scope, receive, send)
            return

        ip = client_ip(HTTPConnection(scope))
        key = f"ratelimit:api:{ip}:{int(time.time() // 60)}"
        count = 0
        try:
            count = int(await resolve(redis_client.incr(key)))
            if count == 1:
                await resolve(redis_client.expire(key, 60))
        except (RedisError, OSError):
            logger.warning("rate limiter unavailable; allowing request")
        if count > limit:
            body = json.dumps(
                {"error": {"code": "rate_limited", "message": "Too many requests", "details": None}}
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"retry-after", b"60"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Basic OWASP-oriented response headers for the API."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        hardened = settings.cookie_secure or settings.app_env == "production"

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Content-Type-Options", "nosniff")
                headers.append("X-Frame-Options", "DENY")
                headers.append("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.append("X-XSS-Protection", "0")
                if hardened:
                    headers.append(
                        "Strict-Transport-Security",
                        "max-age=31536000; includeSubDomains; preload",
                    )
                    headers.append(
                        "Content-Security-Policy",
                        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
                    )
            await send(message)

        await self.app(scope, receive, send_with_headers)
