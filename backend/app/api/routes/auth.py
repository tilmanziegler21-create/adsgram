"""Adsgram auth via Telegram Login Widget."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.telegram_auth import verify_telegram_login, verify_webapp_init_data
from app.services.telegram_bot import normalize_bot_username, resolve_bot_username
from app.store.memory import store

router = APIRouter()


class TelegramLoginIn(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str = Field(..., min_length=1)


class UserProfileOut(BaseModel):
    id: str
    telegram_id: str
    telegram_username: str | None
    telegram_first_name: str | None
    balance: int


class AuthConfigOut(BaseModel):
    bot_username: str | None
    bot_link: str | None = None


class TelegramWebAppIn(BaseModel):
    init_data: str = Field(..., min_length=1)


def _profile(user) -> UserProfileOut:
    return UserProfileOut(
        id=user.id,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        telegram_first_name=user.telegram_first_name,
        balance=user.balance,
    )


@router.get("/config", response_model=AuthConfigOut)
async def auth_config():
    username = await resolve_bot_username()
    bot_link = f"https://t.me/{username}" if username else None
    return AuthConfigOut(bot_username=username, bot_link=bot_link)


@router.post("/telegram", response_model=UserProfileOut)
async def telegram_login(payload: TelegramLoginIn):
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")

    data = payload.model_dump(exclude_none=True)
    if not verify_telegram_login(data):
        raise HTTPException(status_code=401, detail="Invalid Telegram auth data")

    user = store.get_or_create_telegram_user(
        telegram_id=str(payload.id),
        username=payload.username,
        first_name=payload.first_name,
    )
    return _profile(user)


@router.post("/telegram-webapp", response_model=UserProfileOut)
async def telegram_webapp_login(payload: TelegramWebAppIn):
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")

    tg_user = verify_webapp_init_data(payload.init_data)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid Telegram WebApp data")

    user = store.get_or_create_telegram_user(
        telegram_id=str(tg_user["id"]),
        username=tg_user.get("username"),
        first_name=tg_user.get("first_name"),
    )
    return _profile(user)


@router.get("/me", response_model=UserProfileOut)
async def get_profile(user_id: str):
    user = store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _profile(user)
