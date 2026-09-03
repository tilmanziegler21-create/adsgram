"""Parse Telegram groups/channels for target audience."""

from __future__ import annotations

import asyncio
import uuid

from hydrogram.errors import FloodWait

from workers.celery_app import celery_app
from workers.db.models import Campaign, CampaignStatus, TelegramAccount
from workers.db.session import get_session
from workers.services.account_pool import (
    assign_account,
    get_account_with_proxy,
    pick_available_account,
)
from workers.services.audience_parser import parse_audience_links
from workers.services.session_monitor import handle_account_error
from workers.telegram.client import create_client


async def _run_parse(account_id: uuid.UUID, links: list[str]) -> dict:
    with get_session() as session:
        account, proxy = get_account_with_proxy(session, account_id)

    client = create_client(account.session_path, proxy=proxy)
    await client.start()
    try:
        return {"targets": await parse_audience_links(client, links)}
    finally:
        await client.stop()


@celery_app.task(name="workers.parse_audience", bind=True, max_retries=2)
def parse_audience(self, campaign_id: str):
    cid = uuid.UUID(campaign_id)

    with get_session() as session:
        campaign = session.get(Campaign, cid)
        if campaign is None:
            return {"campaign_id": campaign_id, "status": "not_found"}

        links = campaign.audience_links or []
        if not links:
            return {"campaign_id": campaign_id, "status": "no_links"}

        campaign.status = CampaignStatus.parsing
        account = pick_available_account(session, campaign_id=cid)
        if account is None:
            campaign.status = CampaignStatus.failed
            return {"campaign_id": campaign_id, "status": "no_account"}

        assign_account(session, account, cid)
        account_id = account.id
        session.flush()

    try:
        result = asyncio.run(_run_parse(account_id, links))
    except FloodWait as exc:
        with get_session() as session:
            campaign = session.get(Campaign, cid)
            account = session.get(TelegramAccount, account_id)
            if account and campaign:
                handle_account_error(session, account, exc, campaign=campaign)
                replacement = pick_available_account(session, campaign_id=cid, exclude_ids=[account.id])
                if replacement and self.request.retries < self.max_retries:
                    raise self.retry(countdown=exc.value + 5)
            if campaign:
                campaign.status = CampaignStatus.failed
        return {
            "campaign_id": campaign_id,
            "status": "flood_wait",
            "seconds": exc.value,
        }
    except Exception as exc:
        with get_session() as session:
            campaign = session.get(Campaign, cid)
            account = session.get(TelegramAccount, account_id)
            if account and campaign:
                handle_account_error(session, account, exc, campaign=campaign)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=15)
        with get_session() as session:
            campaign = session.get(Campaign, cid)
            if campaign:
                campaign.status = CampaignStatus.failed
        raise

    targets = result.get("targets", [])
    validated = [t for t in targets if t.get("validated")]

    with get_session() as session:
        campaign = session.get(Campaign, cid)
        if campaign:
            campaign.target_chats = targets
            campaign.status = CampaignStatus.draft if campaign.offer_text else CampaignStatus.draft
            session.flush()

    return {
        "campaign_id": campaign_id,
        "status": "ok",
        "targets_parsed": len(targets),
        "targets_validated": len(validated),
    }
