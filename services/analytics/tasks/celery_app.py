"""Celery application configuration for analytics worker."""

import os

from celery import Celery

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/2")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "analytics",
    broker=broker_url,
    backend=result_backend,
    include=["services.analytics.tasks.export_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "cleanup-expired-exports": {
            "task": "services.analytics.tasks.export_tasks.cleanup_expired_exports",
            "schedule": 86400.0,  # Once per day
        },
    },
)
