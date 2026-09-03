"""Account pool: assign, rotate, flood-wait isolation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from workers.db.models import AccountStatus, Campaign, Proxy, TelegramAccount
from workers.telegram.client import ProxyConfig


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _proxy_config(proxy: Proxy | None) -> ProxyConfig | None:
    if proxy is None or not proxy.is_active:
        return None
    return ProxyConfig(
        scheme=proxy.protocol or "socks5",
        hostname=proxy.host,
        port=proxy.port,
        username=proxy.username,
        password=proxy.password,
    )


def get_account_with_proxy(session: Session, account_id: uuid.UUID) -> tuple[TelegramAccount, ProxyConfig | None]:
    account = session.get(TelegramAccount, account_id)
    if account is None:
        raise ValueError(f"Account not found: {account_id}")
    proxy = session.get(Proxy, account.proxy_id) if account.proxy_id else None
    return account, _proxy_config(proxy)


def pick_available_account(
    session: Session,
    *,
    campaign_id: uuid.UUID | None = None,
    exclude_ids: list[uuid.UUID] | None = None,
) -> TelegramAccount | None:
    """Select reserve/active account not in flood wait and under daily limit."""
    now = _utcnow()
    exclude_ids = exclude_ids or []
    stmt = select(TelegramAccount).where(
        TelegramAccount.status.in_([AccountStatus.active, AccountStatus.reserved]),
        TelegramAccount.daily_sent_count < TelegramAccount.daily_limit,
    )
    if exclude_ids:
        stmt = stmt.where(TelegramAccount.id.not_in(exclude_ids))
    candidates = session.execute(stmt).scalars().all()

    for account in candidates:
        if account.flood_wait_until and account.flood_wait_until > now:
            continue
        if campaign_id and account.assigned_campaign_id and account.assigned_campaign_id != campaign_id:
            continue
        return account
    return None


def assign_account(session: Session, account: TelegramAccount, campaign_id: uuid.UUID) -> None:
    account.assigned_campaign_id = campaign_id
    if account.status == AccountStatus.reserved:
        account.status = AccountStatus.active


def mark_flood_wait(session: Session, account: TelegramAccount, seconds: int) -> None:
    account.status = AccountStatus.flood_wait
    account.flood_wait_until = _utcnow() + timedelta(seconds=seconds)


def mark_banned(session: Session, account: TelegramAccount) -> None:
    account.status = AccountStatus.banned
    account.assigned_campaign_id = None


def release_account(session: Session, account: TelegramAccount) -> None:
    account.assigned_campaign_id = None
    if account.status not in (AccountStatus.banned, AccountStatus.disabled):
        account.status = AccountStatus.reserved


def increment_sent(session: Session, account: TelegramAccount) -> None:
    account.daily_sent_count += 1


def rotate_account(
    session: Session,
    campaign: Campaign,
    failed_account: TelegramAccount,
    reason: str,
) -> TelegramAccount | None:
    """Isolate failed account and attach reserve from pool."""
    if reason == "banned":
        mark_banned(session, failed_account)
    elif reason == "flood_wait":
        # flood_wait_until already set by caller
        failed_account.assigned_campaign_id = None
    else:
        release_account(session, failed_account)

    replacement = pick_available_account(
        session,
        campaign_id=campaign.id,
        exclude_ids=[failed_account.id],
    )
    if replacement:
        assign_account(session, replacement, campaign.id)
    return replacement
