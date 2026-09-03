"""Telegram Bot API helpers."""

from __future__ import annotations

import httpx

from app.core.config import settings

_cached_username: str | None = None


def normalize_bot_username(value: str | None) -> str | None:
    if not value:
        return None
    username = value.strip().lstrip("@").strip()
    return username or None


async def resolve_bot_username() -> str | None:
    """Return bot username for Login Widget (env or Telegram getMe)."""
    global _cached_username

    configured = normalize_bot_username(settings.TELEGRAM_BOT_USERNAME)
    if configured:
        return configured

    if _cached_username:
        return _cached_username

    token = settings.TELEGRAM_BOT_TOKEN.strip()
    if not token:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            response.raise_for_status()
            username = response.json().get("result", {}).get("username")
            _cached_username = normalize_bot_username(username)
            return _cached_username
    except Exception:
        return None
