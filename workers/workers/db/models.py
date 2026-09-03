"""ORM mirror for worker DB access (sync)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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


class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(32))
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean)


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    session_path: Mapped[str] = mapped_column(String(512))
    status: Mapped[AccountStatus] = mapped_column(Enum(AccountStatus, name="account_status"))
    proxy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("proxies.id"))
    daily_sent_count: Mapped[int] = mapped_column(Integer)
    daily_limit: Mapped[int] = mapped_column(Integer)
    flood_wait_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus, name="campaign_status"))
    knowledge_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    knowledge_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    knowledge_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_base: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    audience_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_links: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_chats: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    offer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    messages_sent: Mapped[int] = mapped_column(Integer)
    active_dialogs: Mapped[int] = mapped_column(Integer)
    smart_shield_ok: Mapped[bool] = mapped_column(Boolean)


class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("telegram_accounts.id"), nullable=True
    )
    telegram_chat_id: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean)
    messages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
