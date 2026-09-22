"""
Celery Application Configuration (PRD Section 9)
================================================
Celery app instance used by all background tasks. Redis serves as both
the message broker and the result backend.
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "campaigniq",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.jobs.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Fair dispatch: one task at a time per worker
    task_acks_late=True,           # Acknowledge only after task completes (safer retries)
    task_reject_on_worker_lost=True,
    # Crawl/send enqueueing happens after the API transaction. A missing
    # worker or unavailable broker must not hold an HTTP request open for the
    # broker's default retry window; the persisted job remains visible for a
    # later worker retry/manual operational recovery.
    broker_connection_timeout=2,
    broker_connection_max_retries=1,
    broker_connection_retry_on_startup=False,
)
