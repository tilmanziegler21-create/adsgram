"""Telegram Bot API for Adsgram publishing and notifications."""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.store.memory import ChannelRecord, OrderRecord


def _bot_url(method: str) -> str:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    return f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


async def _post(method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_bot_url(method), json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "Telegram API error"))
        return data["result"]


async def publish_ad_to_channel(channel: ChannelRecord, post_text: str) -> int:
    result = await _post(
        "sendMessage",
        {
            "chat_id": int(channel.telegram_chat_id),
            "text": post_text,
            "parse_mode": "HTML",
        },
    )
    return int(result["message_id"])


async def notify_owner_ad_request(order: OrderRecord, channel: ChannelRecord | None) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    text = (
        f"📢 <b>Adsgram — запрос на рекламу</b>\n\n"
        f"Канал: <b>{channel.title if channel else '—'}</b>\n"
        f"Срок: <b>{order.duration_hours} ч</b>\n"
        f"Сумма: <b>{order.price}</b> ₽\n\n"
        f"<b>Текст поста:</b>\n{order.post_text}\n\n"
        f"Подтвердите или отклоните размещение."
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Одобрить", "callback_data": f"ad:approve:{order.id}"},
                {"text": "❌ Отклонить", "callback_data": f"ad:reject:{order.id}"},
            ]
        ]
    }
    await _post(
        "sendMessage",
        {
            "chat_id": int(order.owner_telegram_id),
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard,
        },
    )
