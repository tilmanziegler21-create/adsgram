"""Parse website URL / file into campaigns.knowledge_base."""

from __future__ import annotations

import uuid

from workers.celery_app import celery_app
from workers.core.config import settings
from workers.db.models import Campaign, CampaignStatus
from workers.db.session import get_session
from workers.services.knowledge_parser import extract_from_file, extract_from_url


@celery_app.task(
    name="workers.parse_knowledge",
    bind=True,
    max_retries=2,
    soft_time_limit=60,
    time_limit=65,
)
def parse_knowledge(
    self,
    campaign_id: str,
    source_url: str | None = None,
    file_path: str | None = None,
):
    cid = uuid.UUID(campaign_id)

    with get_session() as session:
        campaign = session.get(Campaign, cid)
        if campaign is None:
            return {"campaign_id": campaign_id, "status": "not_found"}

        campaign.status = CampaignStatus.parsing
        session.flush()

    try:
        if source_url:
            knowledge_base = extract_from_url(
                source_url,
                timeout=float(settings.KNOWLEDGE_PARSE_TIMEOUT_SEC),
            )
        elif file_path:
            knowledge_base = extract_from_file(file_path)
        else:
            return {"campaign_id": campaign_id, "status": "no_source"}

        with get_session() as session:
            campaign = session.get(Campaign, cid)
            if campaign is None:
                return {"campaign_id": campaign_id, "status": "not_found"}

            campaign.knowledge_base = knowledge_base
            campaign.knowledge_text = knowledge_base.get("text", "")
            if source_url:
                campaign.knowledge_url = source_url
            if file_path:
                campaign.knowledge_file_path = file_path
            campaign.status = CampaignStatus.draft
            session.flush()

        return {
            "campaign_id": campaign_id,
            "status": "ok",
            "char_count": knowledge_base.get("char_count", 0),
            "duration_sec": knowledge_base.get("duration_sec"),
        }
    except Exception as exc:
        with get_session() as session:
            campaign = session.get(Campaign, cid)
            if campaign:
                campaign.status = CampaignStatus.failed
                campaign.knowledge_base = {
                    "error": str(exc),
                    "source_url": source_url,
                    "source_path": file_path,
                }
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)
        return {"campaign_id": campaign_id, "status": "error", "error": str(exc)}
