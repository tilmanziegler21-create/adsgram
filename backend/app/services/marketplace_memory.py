"""Adsgram marketplace logic (in-memory)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.store.memory import DEFAULT_PRICING, ChannelRecord, OrderRecord, store
from app.services.telegram_publisher import notify_owner_ad_request, publish_ad_to_channel


def resolve_price(channel: ChannelRecord, duration_hours: int) -> int:
    for option in channel.pricing:
        if option.get("duration_hours") == duration_hours:
            return int(option["price"])
    raise ValueError(f"Duration {duration_hours}h is not available for this channel")


def create_order(
    *,
    advertiser_user_id: str,
    channel_id: str,
    post_text: str,
    duration_hours: int,
    post_media: dict | None = None,
) -> OrderRecord:
    channel = store.get_channel(channel_id)
    if not channel or not channel.is_active or not channel.can_post:
        raise ValueError("Channel is not available for ads")

    order = OrderRecord(
        id=str(__import__("uuid").uuid4()),
        advertiser_user_id=advertiser_user_id,
        channel_id=channel_id,
        post_text=post_text,
        post_media=post_media,
        duration_hours=duration_hours,
        price=resolve_price(channel, duration_hours),
        status="pending_payment",
        owner_telegram_id=channel.owner_telegram_id,
    )
    with store._lock:
        store.orders[order.id] = order
    return order


async def pay_order(order_id: str, advertiser_user_id: str) -> OrderRecord:
    with store._lock:
        order = store.orders.get(order_id)
        if not order or order.advertiser_user_id != advertiser_user_id:
            raise ValueError("Order not found")
        if order.status != "pending_payment":
            raise ValueError("Order is not awaiting payment")

        user = store.users.get(advertiser_user_id)
        if not user or user.balance < order.price:
            raise ValueError("Insufficient balance")

        user.balance -= order.price
        store.add_transaction(
            advertiser_user_id,
            -order.price,
            "ad_payment",
            "Оплата рекламы",
            order.id,
        )

        order.status = "awaiting_owner"
        channel = store.channels.get(order.channel_id)
        if channel:
            channel.total_orders += 1

    await notify_owner_ad_request(order, channel)
    order.owner_notified_at = datetime.now(timezone.utc).isoformat()
    return order


async def approve_order(order_id: str, owner_telegram_id: str) -> OrderRecord:
    with store._lock:
        order = store.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.owner_telegram_id != owner_telegram_id:
            raise PermissionError("Not channel owner")
        if order.status != "awaiting_owner":
            raise ValueError("Order is not awaiting approval")
        channel = store.channels.get(order.channel_id)
        if not channel:
            raise ValueError("Channel not found")

    message_id = await publish_ad_to_channel(channel, order.post_text)
    now = datetime.now(timezone.utc)

    with store._lock:
        order = store.orders[order_id]
        order.status = "published"
        order.published_message_id = message_id
        order.published_at = now.isoformat()
        order.expires_at = (now + timedelta(hours=order.duration_hours)).isoformat()

        channel = store.channels[order.channel_id]
        channel.completed_orders += 1
        channel.rating = min(5.0, 4.0 + channel.completed_orders * 0.05)

        owner_user = _find_owner_user(owner_telegram_id)
        if owner_user:
            owner_user.balance += order.price
            store.add_transaction(
                owner_user.id,
                order.price,
                "ad_payout",
                "Выплата за размещение рекламы",
                order.id,
            )

    return order


def reject_order(order_id: str, owner_telegram_id: str) -> OrderRecord:
    with store._lock:
        order = store.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.owner_telegram_id != owner_telegram_id:
            raise PermissionError("Not channel owner")
        if order.status != "awaiting_owner":
            raise ValueError("Order is not awaiting approval")

        order.status = "rejected"
        user = store.users.get(order.advertiser_user_id)
        if user:
            user.balance += order.price
            store.add_transaction(
                order.advertiser_user_id,
                order.price,
                "refund",
                "Возврат за отклонённую рекламу",
                order.id,
            )
        return order


def _find_owner_user(telegram_id: str):
    return store.get_or_create_telegram_user(
        telegram_id=telegram_id,
        username=None,
    )


def list_orders_for_user(user_id: str) -> list[OrderRecord]:
    with store._lock:
        orders = [o for o in store.orders.values() if o.advertiser_user_id == user_id]
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders
