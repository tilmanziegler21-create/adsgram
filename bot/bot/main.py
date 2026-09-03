"""Telegram bot: channel connect + ad approval callbacks."""

from __future__ import annotations

import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import CallbackQuery, ChatMemberUpdated

from bot.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def register_channel(payload: dict) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.BACKEND_URL}/api/marketplace/channels/register",
            json=payload,
        )
        response.raise_for_status()


async def approve_order(order_id: str, owner_telegram_id: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.BACKEND_URL}/api/marketplace/orders/{order_id}/approve",
            params={"owner_telegram_id": owner_telegram_id},
        )
        response.raise_for_status()
        return response.json()


async def reject_order(order_id: str, owner_telegram_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.BACKEND_URL}/api/marketplace/orders/{order_id}/reject",
            params={"owner_telegram_id": owner_telegram_id},
        )
        response.raise_for_status()
        return response.json()


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER))
    async def bot_added(event: ChatMemberUpdated, bot: Bot) -> None:
        chat = event.chat
        if chat.type not in (ChatType.CHANNEL, ChatType.SUPERGROUP, ChatType.GROUP):
            return

        bot_member = event.new_chat_member
        can_post = bool(getattr(bot_member, "can_post_messages", False))
        if chat.type == ChatType.CHANNEL:
            can_post = True

        if not can_post:
            logger.warning("Bot added to %s without post permission", chat.id)
            return

        admins = await bot.get_chat_administrators(chat.id)
        owner = next((a for a in admins if a.status == ChatMemberStatus.CREATOR), None)
        if owner is None and admins:
            owner = admins[0]
        if owner is None:
            return

        subscribers = await bot.get_chat_member_count(chat.id)

        await register_channel(
            {
                "telegram_chat_id": str(chat.id),
                "chat_type": chat.type,
                "title": chat.title or chat.full_name or "Channel",
                "username": chat.username,
                "owner_telegram_id": str(owner.user.id),
                "subscribers_count": subscribers,
                "can_post": can_post,
            }
        )
        logger.info("Registered channel %s (%s)", chat.title, chat.id)

    @dp.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER))
    async def bot_removed(event: ChatMemberUpdated) -> None:
        logger.info("Bot removed from chat %s", event.chat.id)

    @dp.callback_query(F.data.startswith("ad:approve:"))
    async def on_approve(callback: CallbackQuery) -> None:
        order_id = callback.data.split(":")[-1]
        owner_id = str(callback.from_user.id)
        try:
            await approve_order(order_id, owner_id)
            await callback.message.edit_text("✅ Реклама одобрена и опубликована. Баланс начислен.")
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            await callback.answer(f"Ошибка: {detail}", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("ad:reject:"))
    async def on_reject(callback: CallbackQuery) -> None:
        order_id = callback.data.split(":")[-1]
        owner_id = str(callback.from_user.id)
        try:
            await reject_order(order_id, owner_id)
            await callback.message.edit_text("❌ Реклама отклонена. Средства возвращены рекламодателю.")
        except httpx.HTTPStatusError as exc:
            await callback.answer(f"Ошибка: {exc.response.text}", show_alert=True)
        await callback.answer()

    return dp


async def main() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
