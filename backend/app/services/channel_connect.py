"""Connect Telegram channels via Bot API."""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.store.memory import ChannelRecord, store


class ChannelConnectError(Exception):
    pass


def parse_channel_username(raw: str) -> str:
    value = raw.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    return value.lstrip("@").split("/")[0].split("?")[0].strip()


async def _tg_api(method: str, **params: object) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ChannelConnectError("Telegram bot is not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=params,
        )
        data = response.json()
        if not data.get("ok"):
            description = data.get("description", "Telegram API error")
            if "chat not found" in description.lower():
                raise ChannelConnectError("Канал не найден. Проверьте @username.")
            if "not enough rights" in description.lower():
                raise ChannelConnectError("Бот не добавлен в канал или нет прав.")
            raise ChannelConnectError(description)
        return data["result"]


async def connect_channel(owner_telegram_id: str, channel_input: str) -> ChannelRecord:
    username = parse_channel_username(channel_input)
    if not username:
        raise ChannelConnectError("Укажите @username или ссылку t.me/канал")

    chat = await _tg_api("getChat", chat_id=f"@{username}")
    chat_id = str(chat["id"])
    chat_type = chat.get("type", "channel")

    bot = await _tg_api("getMe")
    bot_member = await _tg_api("getChatMember", chat_id=chat_id, user_id=bot["id"])
    bot_status = bot_member.get("status")
    if bot_status not in ("administrator", "creator"):
        raise ChannelConnectError(
            "Сначала добавьте бота администратором канала с правом публиковать посты."
        )

    can_post = bool(bot_member.get("can_post_messages", False))
    if chat_type == "channel":
        can_post = bot_status in ("administrator", "creator")
    if not can_post:
        raise ChannelConnectError("Дайте боту право «Публиковать сообщения».")

    admins = await _tg_api("getChatAdministrators", chat_id=chat_id)
    owner_id = int(owner_telegram_id)
    is_admin = any(
        admin["user"]["id"] == owner_id and admin["status"] in ("creator", "administrator")
        for admin in admins
    )
    if not is_admin:
        raise ChannelConnectError("Подключить канал может только его администратор.")

    subscribers = await _tg_api("getChatMemberCount", chat_id=chat_id)

    return store.register_channel(
        telegram_chat_id=chat_id,
        chat_type=chat_type,
        title=chat.get("title") or username,
        username=chat.get("username"),
        owner_telegram_id=owner_telegram_id,
        subscribers_count=subscribers,
        can_post=can_post,
    )
