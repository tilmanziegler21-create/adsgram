"""Celery task status polling for E2E."""

from fastapi import APIRouter

from app.core.celery_client import celery_client

router = APIRouter()


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    result = celery_client.AsyncResult(task_id)
    payload = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
    }
    if result.ready():
        try:
            payload["result"] = result.result
        except Exception as exc:
            payload["result"] = {"error": str(exc)}
    return payload
