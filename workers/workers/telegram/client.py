"""Hydrogram client factory (Pyrogram-compatible, maintained PyPI fork)."""

from __future__ import annotations

from dataclasses import dataclass

from hydrogram import Client

from workers.core.config import settings


@dataclass(frozen=True)
class ProxyConfig:
    scheme: str
    hostname: str
    port: int
    username: str | None = None
    password: str | None = None

    def as_dict(self) -> dict:
        proxy: dict = {
            "scheme": self.scheme,
            "hostname": self.hostname,
            "port": self.port,
        }
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy


def create_client(
    session_name: str,
    *,
    workdir: str | None = None,
    proxy: ProxyConfig | None = None,
) -> Client:
    """Build Hydrogram client. Credentials are server-side only."""
    if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
        raise RuntimeError(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH are not set. Fill them in .env (server-side only)."
        )
    return Client(
        name=session_name,
        api_id=settings.TELEGRAM_API_ID,
        api_hash=settings.TELEGRAM_API_HASH,
        workdir=workdir or settings.TELEGRAM_SESSIONS_DIR,
        proxy=proxy.as_dict() if proxy else None,
    )
