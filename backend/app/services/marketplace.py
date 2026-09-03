"""Ad marketplace business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AdOrder, AdOrderStatus, ConnectedChannel, CreditBalance, User, WalletTransaction
from app.services.telegram_publisher import notify_owner_ad_request, publish_ad_to_channel

DEFAULT_PRICING = [
    {"duration_hours": 24, "label": "1 день", "price": 500},
    {"duration_hours": 48, "label": "2 дня", "price": 900},
    {"duration_hours": 168, "label": "7 дней", "price": 2500},
]


async def get_or_create_balance(session: AsyncSession, user_id: uuid.UUID) -> CreditBalance:
    result = await session.execute(select(CreditBalance).where(CreditBalance.user_id == user_id))
    balance = result.scalar_one_or_none()
    if balance is None:
        balance = CreditBalance(user_id=user_id, balance=0)
        session.add(balance)
        await session.flush()
    return balance


def resolve_price(channel: ConnectedChannel, duration_hours: int) -> int:
    pricing = channel.pricing or DEFAULT_PRICING
    for option in pricing:
        if option.get("duration_hours") == duration_hours:
            return int(option["price"])
    raise ValueError(f"Duration {duration_hours}h is not available for this channel")


async def register_channel(
    session: AsyncSession,
    *,
    telegram_chat_id: str,
    chat_type: str,
    title: str,
    username: str | None,
    owner_telegram_id: str,
    subscribers_count: int,
    can_post: bool,
) -> ConnectedChannel:
    stmt = select(ConnectedChannel).where(ConnectedChannel.telegram_chat_id == telegram_chat_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()

    owner_user = None
    user_stmt = select(User).where(User.telegram_id == owner_telegram_id)
    owner_user = (await session.execute(user_stmt)).scalar_one_or_none()

    if existing:
        existing.title = title
        existing.username = username
        existing.owner_telegram_id = owner_telegram_id
        existing.owner_user_id = owner_user.id if owner_user else existing.owner_user_id
        existing.subscribers_count = subscribers_count
        existing.can_post = can_post
        existing.is_active = can_post
        existing.stats = {
            **(existing.stats or {}),
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
        }
        channel = existing
    else:
        channel = ConnectedChannel(
            telegram_chat_id=telegram_chat_id,
            chat_type=chat_type,
            title=title,
            username=username,
            owner_telegram_id=owner_telegram_id,
            owner_user_id=owner_user.id if owner_user else None,
            subscribers_count=subscribers_count,
            can_post=can_post,
            is_active=can_post,
            pricing=DEFAULT_PRICING,
            stats={"connected_at": datetime.now(timezone.utc).isoformat()},
        )
        session.add(channel)

    await session.flush()
    await session.refresh(channel)
    return channel


async def create_ad_order(
    session: AsyncSession,
    *,
    advertiser_user_id: uuid.UUID,
    channel_id: uuid.UUID,
    post_text: str,
    duration_hours: int,
    post_media: dict | None = None,
) -> AdOrder:
    channel = await session.get(ConnectedChannel, channel_id)
    if not channel or not channel.is_active or not channel.can_post:
        raise ValueError("Channel is not available for ads")

    price = resolve_price(channel, duration_hours)
    order = AdOrder(
        advertiser_user_id=advertiser_user_id,
        channel_id=channel_id,
        post_text=post_text,
        post_media=post_media,
        duration_hours=duration_hours,
        price=price,
        status=AdOrderStatus.pending_payment,
        owner_telegram_id=channel.owner_telegram_id,
    )
    session.add(order)
    await session.flush()
    await session.refresh(order)
    return order


async def pay_ad_order(session: AsyncSession, order_id: uuid.UUID, advertiser_user_id: uuid.UUID) -> AdOrder:
    stmt = select(AdOrder).where(AdOrder.id == order_id).options(selectinload(AdOrder.channel))
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order or order.advertiser_user_id != advertiser_user_id:
        raise ValueError("Order not found")
    if order.status != AdOrderStatus.pending_payment:
        raise ValueError("Order is not awaiting payment")

    balance = await get_or_create_balance(session, advertiser_user_id)
    if balance.balance < order.price:
        raise ValueError("Insufficient balance")

    balance.balance -= order.price
    session.add(
        WalletTransaction(
            user_id=advertiser_user_id,
            amount=-order.price,
            kind="ad_payment",
            reference_id=str(order.id),
            description=f"Оплата рекламы в «{order.channel.title if order.channel else ''}»",
        )
    )

    order.status = AdOrderStatus.awaiting_owner
    channel = await session.get(ConnectedChannel, order.channel_id)
    if channel:
        channel.total_orders += 1

    await session.flush()
    await notify_owner_ad_request(order)
    order.owner_notified_at = datetime.now(timezone.utc)
    await session.refresh(order)
    return order


async def approve_ad_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    owner_telegram_id: str,
) -> AdOrder:
    stmt = select(AdOrder).where(AdOrder.id == order_id).options(selectinload(AdOrder.channel))
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order:
        raise ValueError("Order not found")
    if order.owner_telegram_id != owner_telegram_id:
        raise PermissionError("Not channel owner")
    if order.status != AdOrderStatus.awaiting_owner:
        raise ValueError("Order is not awaiting approval")

    order.status = AdOrderStatus.approved
    await session.flush()

    message_id = await publish_ad_to_channel(order)
    order.published_message_id = message_id
    order.published_at = datetime.now(timezone.utc)
    order.expires_at = order.published_at + timedelta(hours=order.duration_hours)
    order.status = AdOrderStatus.published

    channel = await session.get(ConnectedChannel, order.channel_id)
    if channel:
        channel.completed_orders += 1
        if channel.completed_orders > 0:
            channel.rating = min(5.0, 4.0 + channel.completed_orders * 0.05)

    owner_user_id = channel.owner_user_id if channel else None
    if channel and not owner_user_id:
        user_stmt = select(User).where(User.telegram_id == owner_telegram_id)
        owner_user = (await session.execute(user_stmt)).scalar_one_or_none()
        if owner_user is None:
            owner_user = User(
                email=f"tg_{owner_telegram_id}@teleflow.local",
                hashed_password="telegram-linked",
                telegram_id=owner_telegram_id,
            )
            session.add(owner_user)
            await session.flush()
        channel.owner_user_id = owner_user.id
        owner_user_id = owner_user.id

    if owner_user_id:
        owner_balance = await get_or_create_balance(session, owner_user_id)
        owner_balance.balance += order.price
        session.add(
            WalletTransaction(
                user_id=owner_user_id,
                amount=order.price,
                kind="ad_payout",
                reference_id=str(order.id),
                description="Выплата за размещение рекламы",
            )
        )

    await session.flush()
    await session.refresh(order)
    return order


async def reject_ad_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    owner_telegram_id: str,
) -> AdOrder:
    order = await session.get(AdOrder, order_id)
    if not order:
        raise ValueError("Order not found")
    if order.owner_telegram_id != owner_telegram_id:
        raise PermissionError("Not channel owner")
    if order.status != AdOrderStatus.awaiting_owner:
        raise ValueError("Order is not awaiting approval")

    order.status = AdOrderStatus.rejected
    balance = await get_or_create_balance(session, order.advertiser_user_id)
    balance.balance += order.price
    session.add(
        WalletTransaction(
            user_id=order.advertiser_user_id,
            amount=order.price,
            kind="refund",
            reference_id=str(order.id),
            description="Возврат за отклонённую рекламу",
        )
    )
    await session.flush()
    await session.refresh(order)
    return order
