from starlette.requests import HTTPConnection

from app.core.config import get_settings


def client_ip(request: HTTPConnection) -> str:
    """Caller IP. X-Forwarded-For is only trusted when the API sits behind our own proxy."""
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"
