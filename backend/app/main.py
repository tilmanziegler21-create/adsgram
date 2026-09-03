"""TelegramFlow Backend — FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.security import validate_production_settings
from app.store.memory import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_settings()
    if not store.list_channels():
        store.register_channel(
            telegram_chat_id="-1009990001",
            chat_type="channel",
            title="Tech & Crypto Daily",
            username="adsgram_demo",
            owner_telegram_id="100000001",
            subscribers_count=24800,
            can_post=True,
        )
    yield


app = FastAPI(
    title="Adsgram API",
    version="0.2.0",
    lifespan=lifespan,
)

def _cors_origins() -> list[str]:
    origins = list(settings.CORS_ORIGINS)
    if settings.FRONTEND_URL:
        url = settings.FRONTEND_URL.rstrip("/")
        if url not in origins:
            origins.append(url)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
