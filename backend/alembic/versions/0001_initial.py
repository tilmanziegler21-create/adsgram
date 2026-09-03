"""Initial schema for TelegramFlow.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

account_status = sa.Enum(
    "active",
    "flood_wait",
    "banned",
    "reserved",
    "disabled",
    name="account_status",
)
campaign_status = sa.Enum(
    "draft",
    "parsing",
    "ready",
    "running",
    "paused",
    "completed",
    "failed",
    name="campaign_status",
)
subscription_status = sa.Enum(
    "active",
    "expired",
    "cancelled",
    name="subscription_status",
)


def upgrade() -> None:
    account_status.create(op.get_bind(), checkfirst=True)
    campaign_status.create(op.get_bind(), checkfirst=True)
    subscription_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "proxies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(32), nullable=False, server_default="socks5"),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", campaign_status, nullable=False, server_default="draft"),
        sa.Column("knowledge_url", sa.String(2048), nullable=True),
        sa.Column("knowledge_file_path", sa.String(512), nullable=True),
        sa.Column("knowledge_text", sa.Text(), nullable=True),
        sa.Column("audience_keywords", sa.Text(), nullable=True),
        sa.Column("audience_links", postgresql.JSONB(), nullable=True),
        sa.Column("target_chats", postgresql.JSONB(), nullable=True),
        sa.Column("offer_text", sa.Text(), nullable=True),
        sa.Column("messages_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_dialogs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("smart_shield_ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_campaigns_user_id", "campaigns", ["user_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])

    op.create_table(
        "telegram_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("session_path", sa.String(512), nullable=False),
        sa.Column("status", account_status, nullable=False, server_default="reserved"),
        sa.Column("proxy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("proxies.id"), nullable=True),
        sa.Column("daily_sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_limit", sa.Integer(), nullable=False, server_default="40"),
        sa.Column("flood_wait_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "assigned_campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_telegram_accounts_status", "telegram_accounts", ["status"])

    op.create_table(
        "dialogs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("telegram_accounts.id"),
            nullable=True,
        ),
        sa.Column("telegram_chat_id", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("messages", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("campaign_id", "telegram_chat_id", name="uq_campaign_chat"),
    )
    op.create_index("ix_dialogs_campaign_id", "dialogs", ["campaign_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("status", subscription_status, nullable=False, server_default="active"),
        sa.Column("plan_name", sa.String(64), nullable=False, server_default="standard"),
        sa.Column("price_usd", sa.Float(), nullable=False, server_default="49.0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cryptobot_invoice_id", sa.String(128), nullable=True),
    )

    op.create_table(
        "credit_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("credit_balances")
    op.drop_table("subscriptions")
    op.drop_index("ix_dialogs_campaign_id", table_name="dialogs")
    op.drop_table("dialogs")
    op.drop_index("ix_telegram_accounts_status", table_name="telegram_accounts")
    op.drop_table("telegram_accounts")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_user_id", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_table("proxies")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    subscription_status.drop(op.get_bind(), checkfirst=True)
    campaign_status.drop(op.get_bind(), checkfirst=True)
    account_status.drop(op.get_bind(), checkfirst=True)
