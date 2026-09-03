"""Session file checks and Hydrogram account health monitoring."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrogram.errors import (
    AuthKeyDuplicated,
    AuthKeyUnregistered,
    FloodWait,
    UserDeactivated,
    UserDeactivatedBan,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from workers.core.config import settings
from workers.db.models import AccountStatus, Campaign, TelegramAccount
from workers.db.session import get_session
from workers.services.account_pool import (
    get_account_with_proxy,
    mark_banned,
    mark_flood_wait,
    rotate_account,
)
from workers.telegram.client import create_client

AUTH_ERRORS = (AuthKeyUnregistered, AuthKeyDuplicated)
DEACTIVATED_ERRORS = (UserDeactivated, UserDeactivatedBan)


@dataclass(frozen=True)
class ErrorClassification:
    kind: str
    seconds: int | None = None
    message: str = ""


def session_file_path(session_name: str) -> Path:
    return Path(settings.TELEGRAM_SESSIONS_DIR) / f"{session_name}.session"


def check_session_file(session_name: str) -> dict:
    path = session_file_path(session_name)
    exists = path.is_file()
    size = path.stat().st_size if exists else 0
    return {
        "session_name": session_name,
        "path": str(path),
        "exists": exists,
        "size_bytes": size,
        "healthy": exists and size > 0,
    }


def classify_telegram_error(exc: BaseException) -> ErrorClassification:
    if isinstance(exc, FloodWait):
        return ErrorClassification(kind="flood_wait", seconds=int(exc.value), message=str(exc))
    if isinstance(exc, DEACTIVATED_ERRORS):
        return ErrorClassification(kind="user_deactivated", message=str(exc))
    if isinstance(exc, AUTH_ERRORS):
        return ErrorClassification(kind="auth_invalid", message=str(exc))
    return ErrorClassification(kind="unknown", message=str(exc))


def mark_disabled(session: Session, account: TelegramAccount, reason: str = "auth_invalid") -> None:
    account.status = AccountStatus.disabled
    account.assigned_campaign_id = None
    account.flood_wait_until = None


def handle_account_error(
    session: Session,
    account: TelegramAccount,
    exc: BaseException,
    *,
    campaign: Campaign | None = None,
) -> ErrorClassification:
    classification = classify_telegram_error(exc)

    if classification.kind == "flood_wait":
        mark_flood_wait(session, account, classification.seconds or 60)
        if campaign:
            rotate_account(session, campaign, account, "flood_wait")
    elif classification.kind == "user_deactivated":
        mark_banned(session, account)
        if campaign:
            rotate_account(session, campaign, account, "banned")
    elif classification.kind == "auth_invalid":
        mark_disabled(session, account, classification.kind)
        if campaign:
            rotate_account(session, campaign, account, "auth_invalid")
    else:
        mark_disabled(session, account, "unknown_error")

    return classification


async def probe_account(account_id: uuid.UUID) -> dict:
    """Connect via Hydrogram and verify session is alive."""
    with get_session() as session:
        account, proxy = get_account_with_proxy(session, account_id)
        file_info = check_session_file(account.session_path)

    result: dict[str, Any] = {
        "account_id": str(account_id),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "session_file": file_info,
        "connected": False,
        "status": "unknown",
        "error": None,
    }

    if not file_info["healthy"]:
        with get_session() as session:
            db_account = session.get(TelegramAccount, account_id)
            if db_account:
                mark_disabled(session, db_account, "missing_session_file")
        result["status"] = "disabled"
        result["error"] = "session_file_missing"
        return result

    client = create_client(account.session_path, proxy=proxy)
    try:
        await client.start()
        me = await client.get_me()
        result["connected"] = True
        result["telegram_user_id"] = me.id
        result["telegram_username"] = me.username
        result["status"] = "active"

        with get_session() as session:
            db_account = session.get(TelegramAccount, account_id)
            if db_account and db_account.status in (AccountStatus.reserved, AccountStatus.flood_wait):
                now = datetime.now(timezone.utc)
                if not db_account.flood_wait_until or db_account.flood_wait_until <= now:
                    db_account.status = AccountStatus.active
    except Exception as exc:
        classification = classify_telegram_error(exc)
        result["status"] = classification.kind
        result["error"] = classification.message

        with get_session() as session:
            db_account = session.get(TelegramAccount, account_id)
            if db_account:
                handle_account_error(session, db_account, exc)
    finally:
        try:
            await client.stop()
        except Exception:
            pass

    return result


def list_accounts_for_monitoring(session: Session) -> list[TelegramAccount]:
    stmt = select(TelegramAccount).where(
        TelegramAccount.status.in_(
            [AccountStatus.active, AccountStatus.reserved, AccountStatus.flood_wait]
        )
    )
    return list(session.execute(stmt).scalars().all())


async def monitor_all_accounts() -> dict:
    with get_session() as session:
        account_ids = [a.id for a in list_accounts_for_monitoring(session)]

    results = [await probe_account(account_id) for account_id in account_ids]
    healthy = sum(1 for r in results if r.get("connected"))
    return {"checked": len(results), "healthy": healthy, "results": results}


def run_monitor_all_accounts() -> dict:
    return asyncio.run(monitor_all_accounts())
