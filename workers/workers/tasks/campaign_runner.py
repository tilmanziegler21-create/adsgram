"""Campaign execution: Hydrogram + LLM Router + Smart-Shield."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from hydrogram.enums import ChatAction
from hydrogram.errors import FloodWait
from sqlalchemy import select

from workers.celery_app import celery_app
from workers.db.models import Campaign, CampaignStatus, Dialog, TelegramAccount
from workers.db.session import get_session
from workers.llm import filter_llm_response, get_llm_adapter
from workers.services.account_pool import (
    assign_account,
    get_account_with_proxy,
    increment_sent,
    pick_available_account,
    rotate_account,
)
from workers.services.session_monitor import handle_account_error
from workers.services.smart_shield import can_send, human_delay, shield_status
from workers.tasks.llm_router import build_messages
from workers.telegram.client import create_client


def _append_message(dialog: Dialog, role: str, content: str) -> list[dict]:
    history = list(dialog.messages or [])
    history.append({"role": role, "content": content, "at": datetime.now(timezone.utc).isoformat()})
    dialog.messages = history[-20:]
    return history


async def _send_with_llm(
    client,
    campaign_id: uuid.UUID,
    account_id: uuid.UUID,
    dialog_id: uuid.UUID,
    chat_id: int | str,
    user_message: str,
) -> str | None:
    with get_session() as session:
        campaign = session.get(Campaign, campaign_id)
        account = session.get(TelegramAccount, account_id)
        dialog = session.get(Dialog, dialog_id)
        if not campaign or not account or not dialog:
            return None

        history = list(dialog.messages or [])
        messages = build_messages(
            campaign.knowledge_text or "",
            campaign.offer_text or "",
            user_message,
            history,
        )

    adapter = get_llm_adapter()
    raw = adapter.chat(messages)
    reply = filter_llm_response(raw)
    if not reply:
        return None

    await client.send_chat_action(chat_id, ChatAction.TYPING)
    human_delay()
    await client.send_message(chat_id, reply)

    with get_session() as session:
        db_dialog = session.get(Dialog, dialog_id)
        db_account = session.get(TelegramAccount, account_id)
        db_campaign = session.get(Campaign, campaign_id)
        if db_dialog and db_account and db_campaign:
            _append_message(db_dialog, "user", user_message)
            _append_message(db_dialog, "assistant", reply)
            increment_sent(session, db_account)
            db_campaign.messages_sent += 1
            db_campaign.smart_shield_ok = shield_status(db_account)["ok"]

    return reply


async def _run_campaign_async(campaign_id: uuid.UUID) -> dict:
    with get_session() as session:
        campaign = session.get(Campaign, campaign_id)
        if campaign is None:
            return {"status": "not_found"}

        if not campaign.target_chats:
            return {"status": "no_targets"}

        account = pick_available_account(session, campaign_id=campaign_id)
        if account is None:
            campaign.status = CampaignStatus.failed
            return {"status": "no_account"}

        assign_account(session, account, campaign_id)
        campaign.status = CampaignStatus.running
        account_id = account.id
        targets = [t for t in (campaign.target_chats or []) if t.get("validated")]
        session.flush()

    sent = 0
    errors: list[dict] = []

    with get_session() as session:
        account, proxy = get_account_with_proxy(session, account_id)

    client = create_client(account.session_path, proxy=proxy)
    await client.start()

    try:
        for target in targets:
            with get_session() as session:
                account = session.get(TelegramAccount, account_id)
                campaign = session.get(Campaign, campaign_id)
                if not account or not campaign or not can_send(account):
                    break

            chat_id = target.get("chat_id")
            if not chat_id:
                continue

            opener_prompt = (
                f"Напиши короткое первое сообщение для чата «{target.get('title', '')}». "
                f"Цель: {campaign.offer_text or 'заинтересовать аудиторию'}."
            )

            with get_session() as session:
                dialog = Dialog(
                    id=uuid.uuid4(),
                    campaign_id=campaign_id,
                    account_id=account_id,
                    telegram_chat_id=str(chat_id),
                    is_active=True,
                    messages=[],
                )
                session.add(dialog)
                session.flush()
                dialog_id = dialog.id

            try:
                reply = await _send_with_llm(
                    client,
                    campaign_id,
                    account_id,
                    dialog_id,
                    int(chat_id),
                    opener_prompt,
                )
                if reply:
                    sent += 1
            except FloodWait as exc:
                with get_session() as session:
                    campaign = session.get(Campaign, campaign_id)
                    account = session.get(TelegramAccount, account_id)
                    if campaign and account:
                        handle_account_error(session, account, exc, campaign=campaign)
                errors.append({"chat_id": chat_id, "error": "flood_wait", "seconds": exc.value})
                break
            except Exception as exc:
                with get_session() as session:
                    campaign = session.get(Campaign, campaign_id)
                    account = session.get(TelegramAccount, account_id)
                    if campaign and account:
                        classification = handle_account_error(session, account, exc, campaign=campaign)
                        errors.append(
                            {"chat_id": chat_id, "error": classification.kind, "detail": classification.message}
                        )
                    else:
                        errors.append({"chat_id": chat_id, "error": str(exc)})

    finally:
        await client.stop()

    with get_session() as session:
        campaign = session.get(Campaign, campaign_id)
        if campaign:
            campaign.active_dialogs = sent
            session.flush()

    return {
        "campaign_id": str(campaign_id),
        "status": "ok",
        "messages_sent": sent,
        "errors": errors,
    }


async def _process_incoming_async(
    campaign_id: uuid.UUID,
    account_id: uuid.UUID,
    chat_id: str,
    text: str,
) -> dict:
    with get_session() as session:
        campaign = session.get(Campaign, campaign_id)
        account = session.get(TelegramAccount, account_id)
        if not campaign or not account:
            return {"status": "not_found"}

        if not can_send(account):
            return {"status": "shield_blocked", "shield": shield_status(account)}

        stmt = select(Dialog).where(
            Dialog.campaign_id == campaign_id,
            Dialog.telegram_chat_id == chat_id,
        )
        dialog = session.execute(stmt).scalar_one_or_none()

        if dialog is None:
            dialog = Dialog(
                id=uuid.uuid4(),
                campaign_id=campaign_id,
                account_id=account_id,
                telegram_chat_id=chat_id,
                is_active=True,
                messages=[],
            )
            session.add(dialog)
            session.flush()

        dialog_id = dialog.id
        account, proxy = get_account_with_proxy(session, account_id)

    client = create_client(account.session_path, proxy=proxy)
    await client.start()
    try:
        reply = await _send_with_llm(
            client, campaign_id, account_id, dialog_id, int(chat_id), text
        )
        return {"status": "ok" if reply else "filtered", "reply": reply}
    except FloodWait as exc:
        with get_session() as session:
            campaign = session.get(Campaign, campaign_id)
            account = session.get(TelegramAccount, account_id)
            if campaign and account:
                handle_account_error(session, account, exc, campaign=campaign)
        return {"status": "flood_wait", "seconds": exc.value}
    finally:
        await client.stop()


@celery_app.task(name="workers.run_campaign", bind=True)
def run_campaign(self, campaign_id: str):
    return asyncio.run(_run_campaign_async(uuid.UUID(campaign_id)))


@celery_app.task(name="workers.process_incoming", bind=True)
def process_incoming_message(
    self,
    campaign_id: str,
    account_id: str,
    chat_id: str,
    text: str,
):
    """Event chain: incoming message -> LLM Router -> outbound with delays."""
    return asyncio.run(
        _process_incoming_async(
            uuid.UUID(campaign_id),
            uuid.UUID(account_id),
            chat_id,
            text,
        )
    )


@celery_app.task(name="workers.rotate_account", bind=True)
def rotate_account_task(self, campaign_id: str, account_id: str, reason: str):
    with get_session() as session:
        campaign = session.get(Campaign, uuid.UUID(campaign_id))
        account = session.get(TelegramAccount, uuid.UUID(account_id))
        if not campaign or not account:
            return {"status": "not_found"}
        replacement = rotate_account(session, campaign, account, reason)
        return {
            "campaign_id": campaign_id,
            "status": "ok",
            "replacement_account_id": str(replacement.id) if replacement else None,
        }
