"""Telegram bot: channel connect + ad approval callbacks."""

from __future__ import annotations

import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from bot.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _user_label(message: Message) -> str:
    user = message.from_user
    if not user:
        return "друг"
    return user.first_name or user.username or "друг"


def _profile_block(message: Message) -> str:
    user = message.from_user
    if not user:
        return ""
    lines = [f"🆔 Ваш ID: <code>{user.id}</code>"]
    if user.username:
        lines.append(f"👤 Username: @{user.username}")
    else:
        lines.append("👤 Username: не задан (на сайте вход по ID)")
    return "\n".join(lines)


def _site_keyboard() -> InlineKeyboardMarkup | None:
    site = settings.public_site_url()
    if not site:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить канал", web_app=WebAppInfo(url=f"{site}/add-channel/"))],
            [InlineKeyboardButton(text="🌐 Каталог", web_app=WebAppInfo(url=f"{site}/"))],
            [InlineKeyboardButton(text="🔐 Войти", web_app=WebAppInfo(url=f"{site}/login/"))],
        ]
    )


def _welcome_text(message: Message) -> str:
    site = settings.public_site_url()
    site_line = f"\n🌐 Сайт: {site}" if site else ""
    return (
        f"Привет, <b>{_user_label(message)}</b>! 👋\n\n"
        "Я бот <b>Adsgram</b> — маркетплейс рекламы в Telegram-каналах.\n\n"
        f"{_profile_block(message)}\n"
        f"{site_line}\n\n"
        "<b>Команды:</b>\n"
        "/start — это сообщение\n"
        "/addchannel — подключить канал\n"
        "/help — инструкция\n"
        "/id — ваш Telegram ID\n\n"
        "<b>Владельцам каналов:</b> /addchannel или кнопка «Добавить канал».\n\n"
        "<b>Рекламодателям:</b> нажмите «Войти» ниже — вход без привязки домена."
    )


def _help_text() -> str:
    return (
        "<b>Как подключить канал</b>\n"
        "1. Добавьте бота администратором в канал\n"
        "2. Включите право «Публиковать сообщения»\n"
        "3. Канал автоматически появится в каталоге\n\n"
        "<b>Как купить рекламу</b>\n"
        "1. Нажмите кнопку «Войти» в этом боте\n"
        "2. Выберите канал в каталоге\n"
        "3. Оформите заказ\n\n"
        "<b>Одобрение рекламы</b>\n"
        "Владелец канала получает сообщение с кнопками «Одобрить» / «Отклонить».\n\n"
        "По вопросам: напишите сюда любое сообщение — бот ответит."
    )


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


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать"),
            BotCommand(command="addchannel", description="Добавить канал"),
            BotCommand(command="help", description="Инструкция"),
            BotCommand(command="id", description="Мой Telegram ID"),
        ]
    )
    site = settings.public_site_url()
    if site:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть Adsgram",
                web_app=WebAppInfo(url=f"{site}/"),
            )
        )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            return
        await message.answer(
            _welcome_text(message),
            parse_mode=ParseMode.HTML,
            reply_markup=_site_keyboard(),
        )

    @dp.message(Command("addchannel"))
    async def cmd_addchannel(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            return
        site = settings.public_site_url()
        if site:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Подключить канал",
                            web_app=WebAppInfo(url=f"{site}/add-channel/"),
                        )
                    ]
                ]
            )
            await message.answer(
                "<b>Подключение канала</b>\n\n"
                "1. Нажмите кнопку ниже\n"
                "2. Добавьте бота админом в канал\n"
                "3. Введите @username канала и нажмите «Подключить»",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        else:
            await message.answer(_help_text(), parse_mode=ParseMode.HTML)

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            return
        await message.answer(
            _help_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=_site_keyboard(),
        )

    @dp.message(Command("id"))
    async def cmd_id(message: Message) -> None:
        if message.chat.type != ChatType.PRIVATE:
            return
        await message.answer(
            f"<b>Ваш профиль Telegram</b>\n\n{_profile_block(message)}",
            parse_mode=ParseMode.HTML,
        )

    @dp.message(F.chat.type == ChatType.PRIVATE)
    async def on_private_message(message: Message) -> None:
        if message.text and message.text.startswith("/"):
            return
        await message.answer(
            "Я на связи ✅\n\n"
            f"{_profile_block(message)}\n\n"
            "Напишите /help — инструкция по каналам и рекламе.",
            parse_mode=ParseMode.HTML,
            reply_markup=_site_keyboard(),
        )

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

        if owner.user:
            site = settings.public_site_url()
            site_line = f"\n\nКаталог: {site}/" if site else ""
            try:
                await bot.send_message(
                    owner.user.id,
                    f"✅ Канал <b>{chat.title or 'без названия'}</b> подключён к Adsgram.{site_line}",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                logger.warning("Could not notify owner %s", owner.user.id)

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
    await setup_bot_commands(bot)
    dp = create_dispatcher()
    logger.info("Adsgram bot started (site=%s)", settings.public_site_url() or "not set")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
