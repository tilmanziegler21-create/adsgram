"""Marketplace models: connected channels and ad orders."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
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


class AdOrderStatus(str, enum.Enum):
    draft = "draft"
    pending_payment = "pending_payment"
    awaiting_owner = "awaiting_owner"
    approved = "approved"
    published = "published"
    rejected = "rejected"
    cancelled = "cancelled"
    failed = "failed"


class ConnectedChannel(Base):
    """Channel/group where bot is admin and can post."""

    __tablename__ = "connected_channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_chat_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    chat_type: Mapped[str] = mapped_column(String(32), default="channel", nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_telegram_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    subscribers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_post: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # [{ "duration_hours": 24, "price": 500 }, ...]
    pricing: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User | None"] = relationship(back_populates="owned_channels")
    ad_orders: Mapped[list["AdOrder"]] = relationship(back_populates="channel")


class AdOrder(Base):
    __tablename__ = "ad_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advertiser_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connected_channels.id"), nullable=False, index=True
    )
    post_text: Mapped[str] = mapped_column(Text, nullable=False)
    post_media: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AdOrderStatus] = mapped_column(
        Enum(AdOrderStatus, name="ad_order_status"),
        default=AdOrderStatus.draft,
        nullable=False,
        index=True,
    )
    owner_telegram_id: Mapped[str] = mapped_column(String(64), nullable=False)
    published_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    advertiser: Mapped["User"] = relationship(back_populates="ad_orders", foreign_keys=[advertiser_user_id])
    channel: Mapped["ConnectedChannel"] = relationship(back_populates="ad_orders")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # topup | ad_payment | ad_payout | refund
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="wallet_transactions")
