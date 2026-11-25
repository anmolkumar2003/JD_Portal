import logging
import uuid
from functools import lru_cache

from redis import Redis as SyncRedis
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

redis_client: Redis = Redis.from_url(
    get_settings().redis_url,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

# Candidate ids that are being / have been hard-deleted. CV workers skip these so a queued
# process_document task cannot recreate parsed data for a deleted candidate.
DELETED_CANDIDATES_KEY = "cv:deleted_candidates"
DELETED_CANDIDATES_TTL_SECONDS = 7 * 24 * 3600


def get_redis() -> Redis:
    return redis_client


@lru_cache
def _sync_redis() -> SyncRedis:
    return SyncRedis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def is_candidate_marked_deleted_sync(candidate_id: uuid.UUID) -> bool:
    """Worker-side check. Fails open: if Redis is unreachable the DB existence checks still hold."""
    try:
        return bool(_sync_redis().sismember(DELETED_CANDIDATES_KEY, str(candidate_id)))
    except Exception:
        logger.warning("deleted_candidates_lookup_failed", exc_info=True)
        return False
