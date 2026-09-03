"""Health endpoints under /api."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def api_health():
    return {"status": "ok", "service": "api"}
