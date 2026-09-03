"""In-memory store for Adsgram (channels, orders, users, wallets)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock

DEFAULT_PRICING = [
    {"duration_hours": 24, "label": "1 день", "price": 500},
    {"duration_hours": 48, "label": "2 дня", "price": 900},
    {"duration_hours": 168, "label": "7 дней", "price": 2500},
]


@dataclass
class ChannelRecord:
    id: str
    telegram_chat_id: str
    chat_type: str
    title: str
    username: str | None
    owner_telegram_id: str
    subscribers_count: int
    rating: float
    completed_orders: int
    total_orders: int
    is_active: bool
    can_post: bool
    pricing: list[dict]
    stats: dict
    created_at: str


@dataclass
class OrderRecord:
    id: str
    advertiser_user_id: str
    channel_id: str
    post_text: str
    post_media: dict | None
    duration_hours: int
    price: int
    status: str
    owner_telegram_id: str
    published_message_id: int | None = None
    published_at: str | None = None
    expires_at: str | None = None
    owner_notified_at: str | None = None
    created_at: str = field(default_factory=lambda: _now())


@dataclass
class UserRecord:
    id: str
    telegram_id: str
    telegram_username: str | None
    telegram_first_name: str | None = None
    balance: int = 0


@dataclass
class TransactionRecord:
    id: str
    user_id: str
    amount: int
    kind: str
    description: str | None
    reference_id: str | None
    created_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self.channels: dict[str, ChannelRecord] = {}
        self.channels_by_tg: dict[str, str] = {}
        self.orders: dict[str, OrderRecord] = {}
        self.users: dict[str, UserRecord] = {}
        self.users_by_telegram_id: dict[str, str] = {}
        self.transactions: list[TransactionRecord] = []

    def register_channel(
        self,
        *,
        telegram_chat_id: str,
        chat_type: str,
        title: str,
        username: str | None,
        owner_telegram_id: str,
        subscribers_count: int,
        can_post: bool,
    ) -> ChannelRecord:
        with self._lock:
            existing_id = self.channels_by_tg.get(telegram_chat_id)
            if existing_id:
                ch = self.channels[existing_id]
                ch.title = title
                ch.username = username
                ch.owner_telegram_id = owner_telegram_id
                ch.subscribers_count = subscribers_count
                ch.can_post = can_post
                ch.is_active = can_post
                ch.stats = {**ch.stats, "last_sync_at": _now()}
                return ch

            ch = ChannelRecord(
                id=str(uuid.uuid4()),
                telegram_chat_id=telegram_chat_id,
                chat_type=chat_type,
                title=title,
                username=username,
                owner_telegram_id=owner_telegram_id,
                subscribers_count=subscribers_count,
                rating=5.0,
                completed_orders=0,
                total_orders=0,
                is_active=can_post,
                can_post=can_post,
                pricing=list(DEFAULT_PRICING),
                stats={"connected_at": _now()},
                created_at=_now(),
            )
            self.channels[ch.id] = ch
            self.channels_by_tg[telegram_chat_id] = ch.id
            return ch

    def list_channels(self) -> list[ChannelRecord]:
        with self._lock:
            items = [c for c in self.channels.values() if c.is_active and c.can_post]
            items.sort(key=lambda c: (-c.rating, -c.subscribers_count))
            return items

    def list_channels_by_owner(self, owner_telegram_id: str) -> list[ChannelRecord]:
        with self._lock:
            items = [c for c in self.channels.values() if c.owner_telegram_id == owner_telegram_id]
            items.sort(key=lambda c: c.title.lower())
            return items

    def get_channel(self, channel_id: str) -> ChannelRecord | None:
        with self._lock:
            return self.channels.get(channel_id)

    def get_or_create_telegram_user(
        self,
        *,
        telegram_id: str,
        username: str | None,
        first_name: str | None = None,
    ) -> UserRecord:
        with self._lock:
            uid = self.users_by_telegram_id.get(telegram_id)
            if uid:
                user = self.users[uid]
                if username:
                    user.telegram_username = username
                if first_name:
                    user.telegram_first_name = first_name
                return user
            user = UserRecord(
                id=str(uuid.uuid4()),
                telegram_id=telegram_id,
                telegram_username=username,
                telegram_first_name=first_name,
                balance=0,
            )
            self.users[user.id] = user
            self.users_by_telegram_id[telegram_id] = user.id
            return user

    def get_user(self, user_id: str) -> UserRecord | None:
        with self._lock:
            return self.users.get(user_id)

    def add_transaction(
        self,
        user_id: str,
        amount: int,
        kind: str,
        description: str | None = None,
        reference_id: str | None = None,
    ) -> None:
        with self._lock:
            self.transactions.append(
                TransactionRecord(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    amount=amount,
                    kind=kind,
                    description=description,
                    reference_id=reference_id,
                    created_at=_now(),
                )
            )

    def list_transactions(self, user_id: str, limit: int = 50) -> list[TransactionRecord]:
        with self._lock:
            return [t for t in reversed(self.transactions) if t.user_id == user_id][:limit]


store = MemoryStore()
