"""API router — Adsgram core (in-memory, no PostgreSQL required)."""

from fastapi import APIRouter

from app.api.routes import auth, health, marketplace, wallet
from app.core.config import settings
from app.core.security import is_admin_api_enabled

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])

# Legacy Teleflow modules (PostgreSQL + Celery) — ENABLE_LEGACY_API=true
if settings.ENABLE_LEGACY_API:
    from app.api.routes import admin, campaigns, tasks

    api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
    api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
    if is_admin_api_enabled():
        api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
