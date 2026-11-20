from redis.asyncio import Redis

from app.core.config import get_settings

redis_client: Redis = Redis.from_url(
    get_settings().redis_url,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def get_redis() -> Redis:
    return redis_client
