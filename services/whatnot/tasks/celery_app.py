"""Celery application configuration for Whatnot sync worker."""

import os

from celery import Celery

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/2")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "whatnot",
    broker=broker_url,
    backend=result_backend,
    include=["services.whatnot.tasks.sync_tasks"],
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
        "sync-orders-every-15-min": {
            "task": "services.whatnot.tasks.sync_tasks.periodic_order_sync",
            "schedule": 900.0,  # 15 minutes
        },
        "sync-products-every-hour": {
            "task": "services.whatnot.tasks.sync_tasks.periodic_product_sync",
            "schedule": 3600.0,  # 1 hour
        },
        "sync-livestreams-every-hour": {
            "task": "services.whatnot.tasks.sync_tasks.periodic_livestream_sync",
            "schedule": 3600.0,  # 1 hour
        },
    },
)
