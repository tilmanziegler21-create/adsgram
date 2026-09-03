"""Marketplace tables: channels, ad orders, wallet transactions.

Revision ID: 0003_marketplace
Revises: 0002_knowledge_base
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_marketplace"
down_revision: Union[str, None] = "0002_knowledge_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ad_order_status = sa.Enum(
    "draft",
    "pending_payment",
    "awaiting_owner",
    "approved",
    "published",
    "rejected",
    "cancelled",
    "failed",
    name="ad_order_status",
)


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_id", sa.String(64), nullable=True))
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    ad_order_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "connected_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_chat_id", sa.String(64), nullable=False, unique=True),
        sa.Column("chat_type", sa.String(32), nullable=False, server_default="channel"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("owner_telegram_id", sa.String(64), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("subscribers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("completed_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_post", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pricing", postgresql.JSONB(), nullable=True),
        sa.Column("stats", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_connected_channels_owner", "connected_channels", ["owner_telegram_id"])

    op.create_table(
        "ad_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("advertiser_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connected_channels.id"), nullable=False),
        sa.Column("post_text", sa.Text(), nullable=False),
        sa.Column("post_media", postgresql.JSONB(), nullable=True),
        sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("status", ad_order_status, nullable=False, server_default="draft"),
        sa.Column("owner_telegram_id", sa.String(64), nullable=False),
        sa.Column("published_message_id", sa.BigInteger(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ad_orders_advertiser", "ad_orders", ["advertiser_user_id"])
    op.create_index("ix_ad_orders_channel", "ad_orders", ["channel_id"])
    op.create_index("ix_ad_orders_status", "ad_orders", ["status"])

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("reference_id", sa.String(64), nullable=True),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_wallet_transactions_user", "wallet_transactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_wallet_transactions_user", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_index("ix_ad_orders_status", table_name="ad_orders")
    op.drop_index("ix_ad_orders_channel", table_name="ad_orders")
    op.drop_index("ix_ad_orders_advertiser", table_name="ad_orders")
    op.drop_table("ad_orders")
    op.drop_index("ix_connected_channels_owner", table_name="connected_channels")
    op.drop_table("connected_channels")
    ad_order_status.drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_column("users", "telegram_id")
