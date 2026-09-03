"""Telegram group/channel audience parsing via Hydrogram."""

from __future__ import annotations

import re
from typing import Any

from hydrogram import Client
from hydrogram.errors import FloodWait

_INVITE_RE = re.compile(r"(?:https?://)?t\.me/(?:\+|joinchat/)(?P<invite>[\w-]+)", re.I)
_PUBLIC_RE = re.compile(r"(?:https?://)?t\.me/(?P<slug>[\w_]+)", re.I)


def normalize_link(raw: str) -> str:
    link = raw.strip()
    if link.startswith("@"):
        return f"https://t.me/{link[1:]}"
    if link.startswith("t.me/"):
        return f"https://{link}"
    if not link.startswith("http"):
        return f"https://t.me/{link}"
    return link


def _sample_messages(messages: list[Any], limit: int = 5) -> list[dict]:
    samples: list[dict] = []
    for msg in messages[:limit]:
        if not msg.text:
            continue
        samples.append(
            {
                "id": msg.id,
                "text": msg.text[:500],
                "date": msg.date.isoformat() if msg.date else None,
                "from_user_id": msg.from_user.id if msg.from_user else None,
            }
        )
    return samples


async def parse_chat_audience(client: Client, raw_link: str) -> dict:
    link = normalize_link(raw_link)
    invite_match = _INVITE_RE.search(link)
    if invite_match:
        await client.join_chat(link)

    chat = await client.get_chat(link)
    members_count = None
    try:
        members_count = await client.get_chat_members_count(chat.id)
    except Exception:
        pass

    history = []
    try:
        async for message in client.get_chat_history(chat.id, limit=30):
            history.append(message)
    except Exception:
        pass

    active_users: list[int] = []
    for msg in history:
        if msg.from_user and not msg.from_user.is_bot:
            if msg.from_user.id not in active_users:
                active_users.append(msg.from_user.id)

    return {
        "link": link,
        "chat_id": str(chat.id),
        "title": chat.title or chat.first_name or "",
        "username": chat.username,
        "type": str(chat.type),
        "members_count": members_count,
        "message_samples": _sample_messages(history),
        "active_user_ids": active_users[:50],
        "validated": True,
    }


async def parse_audience_links(client: Client, links: list[str]) -> list[dict]:
    results: list[dict] = []
    for raw in links:
        try:
            results.append(await parse_chat_audience(client, raw))
        except FloodWait as exc:
            results.append(
                {
                    "link": normalize_link(raw),
                    "validated": False,
                    "error": "flood_wait",
                    "flood_wait_seconds": exc.value,
                }
            )
            raise
        except Exception as exc:
            results.append(
                {
                    "link": normalize_link(raw),
                    "validated": False,
                    "error": str(exc),
                }
            )
    return results
