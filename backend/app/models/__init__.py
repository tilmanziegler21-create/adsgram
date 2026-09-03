"""Database models for TelegramFlow."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AccountStatus(str, enum.Enum):
    active = "active"
    flood_wait = "flood_wait"
    banned = "banned"
    reserved = "reserved"
    disabled = "disabled"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    parsing = "parsing"
    ready = "ready"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="user")
    subscription: Mapped["Subscription | None"] = relationship(back_populates="user", uselist=False)
    credit_balance: Mapped["CreditBalance | None"] = relationship(back_populates="user", uselist=False)
    telegram_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    owned_channels: Mapped[list["ConnectedChannel"]] = relationship(back_populates="owner")
    ad_orders: Mapped[list["AdOrder"]] = relationship(
        back_populates="advertiser",
        foreign_keys="AdOrder.advertiser_user_id",
    )
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship(back_populates="user")


class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(32), default="socks5", nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    accounts: Mapped[list["TelegramAccount"]] = relationship(back_populates="proxy")


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    session_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status"),
        default=AccountStatus.reserved,
        nullable=False,
        index=True,
    )
    proxy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proxies.id"), nullable=True
    )
    daily_sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    flood_wait_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    proxy: Mapped["Proxy | None"] = relationship(back_populates="accounts")
    assigned_campaign: Mapped["Campaign | None"] = relationship(
        back_populates="accounts",
        foreign_keys=[assigned_campaign_id],
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        default=CampaignStatus.draft,
        nullable=False,
        index=True,
    )
    # Step 1: knowledge source
    knowledge_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    knowledge_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    knowledge_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_base: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Step 2: audience
    audience_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_links: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_chats: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Step 3: offer + metrics
    offer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_dialogs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    smart_shield_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="campaigns")
    accounts: Mapped[list["TelegramAccount"]] = relationship(
        back_populates="assigned_campaign",
        foreign_keys="TelegramAccount.assigned_campaign_id",
    )
    dialogs: Mapped[list["Dialog"]] = relationship(back_populates="campaign")


class Dialog(Base):
    __tablename__ = "dialogs"
    __table_args__ = (UniqueConstraint("campaign_id", "telegram_chat_id", name="uq_campaign_chat"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("telegram_accounts.id"), nullable=True
    )
    telegram_chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    messages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="dialogs")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.active,
        nullable=False,
    )
    plan_name: Mapped[str] = mapped_column(String(64), default="standard", nullable=False)
    price_usd: Mapped[float] = mapped_column(Float, default=49.0, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cryptobot_invoice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subscription")


class CreditBalance(Base):
    __tablename__ = "credit_balances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="credit_balance")


# Marketplace models (import for Alembic registration)
from app.models.marketplace import AdOrder, AdOrderStatus, ConnectedChannel, WalletTransaction  # noqa: E402, F401
