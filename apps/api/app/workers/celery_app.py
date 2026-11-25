from typing import Any

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()

celery_app = Celery(
    "hr_portal",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

# Always on: retries MinIO deletes that failed after a candidate hard-delete.
beat_schedule: dict[str, dict[str, Any]] = {
    "cleanup-orphan-storage-hourly": {
        "task": "cleanup_orphan_storage",
        "schedule": crontab(minute=7),
    },
}
if settings.retention_rejected_days > 0:
    beat_schedule["retention-rejected-daily"] = {
        "task": "run_retention_rejected",
        "schedule": crontab(hour=3, minute=15),
    }
celery_app.conf.beat_schedule = beat_schedule


@setup_logging.connect
def _configure_worker_logging(**_: Any) -> None:
    configure_logging(settings.log_level)
