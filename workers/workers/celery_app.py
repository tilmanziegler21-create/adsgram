"""Celery application for TelegramFlow workers."""

from celery import Celery
from celery.schedules import crontab

from workers.core.config import settings
from workers.core.security import validate_production_settings

validate_production_settings()

celery_app = Celery(
    "teleflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "workers.tasks.parse_knowledge",
        "workers.tasks.parse_audience",
        "workers.tasks.campaign_runner",
        "workers.tasks.llm_router",
        "workers.tasks.session_monitor",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "monitor-sessions-every-5-min": {
            "task": "workers.monitor_sessions",
            "schedule": crontab(minute="*/5"),
        },
    },
)
