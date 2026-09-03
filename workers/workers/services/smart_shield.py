"""Smart-Shield: human-like delays and daily limit checks."""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone

from workers.core.config import settings
from workers.db.models import TelegramAccount


def human_delay(
    min_seconds: int | None = None,
    max_seconds: int | None = None,
) -> float:
    min_s = min_seconds if min_seconds is not None else settings.SMART_SHIELD_MIN_DELAY
    max_s = max_seconds if max_seconds is not None else settings.SMART_SHIELD_MAX_DELAY
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)
    return delay


def can_send(account: TelegramAccount) -> bool:
    now = datetime.now(timezone.utc)
    if account.daily_sent_count >= account.daily_limit:
        return False
    if account.flood_wait_until and account.flood_wait_until > now:
        return False
    return True


def shield_status(account: TelegramAccount) -> dict:
    now = datetime.now(timezone.utc)
    flood_active = bool(account.flood_wait_until and account.flood_wait_until > now)
    limit_reached = account.daily_sent_count >= account.daily_limit
    ok = can_send(account)
    return {
        "ok": ok,
        "flood_wait_active": flood_active,
        "daily_limit_reached": limit_reached,
        "daily_sent": account.daily_sent_count,
        "daily_limit": account.daily_limit,
    }
