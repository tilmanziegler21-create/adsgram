"""Celery client for dispatching worker tasks from FastAPI."""

from celery import Celery

from app.core.config import settings

celery_client = Celery(
    "teleflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_client.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
