"""Verify Telegram Login Widget and Mini App auth data."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl, unquote

from app.core.config import settings

AUTH_MAX_AGE_SECONDS = 86400


def verify_telegram_login(data: dict[str, Any]) -> bool:
    """Validate hash from Telegram Login Widget (https://core.telegram.org/widgets/login)."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return False

    received_hash = data.get("hash")
    if not received_hash:
        return False

    auth_date = data.get("auth_date")
    if auth_date is None:
        return False
    if time.time() - int(auth_date) > AUTH_MAX_AGE_SECONDS:
        return False

    check_items = {k: v for k, v in data.items() if k != "hash" and v is not None}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(check_items.items()))

    secret_key = hashlib.sha256(token.encode()).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, str(received_hash))


def verify_webapp_init_data(init_data: str) -> dict[str, Any] | None:
    """Validate Telegram Mini App initData and return parsed user dict."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not init_data:
        return None

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    auth_date = parsed.get("auth_date")
    if auth_date is None:
        return None
    if time.time() - int(auth_date) > AUTH_MAX_AGE_SECONDS:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        return None

    user_raw = parsed.get("user")
    if not user_raw:
        return None
    return json.loads(unquote(user_raw))

