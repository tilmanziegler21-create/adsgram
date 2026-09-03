"""Campaign endpoints for 3-step MVP funnel."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_client import celery_client
from app.core.database import get_db
from app.models import Campaign, CampaignStatus

router = APIRouter()


class CampaignCreate(BaseModel):
    user_id: UUID


class KnowledgeUpdate(BaseModel):
    knowledge_url: HttpUrl | None = None
    knowledge_text: str | None = None


class AudienceUpdate(BaseModel):
    audience_keywords: str | None = None
    audience_links: list[str] | None = None


class OfferUpdate(BaseModel):
    offer_text: str


class TaskDispatchOut(BaseModel):
    task_id: str
    task_name: str
    campaign_id: UUID


class CampaignOut(BaseModel):
    id: UUID
    status: CampaignStatus
    knowledge_url: str | None = None
    knowledge_text: str | None = None
    knowledge_base: dict | None = None
    audience_keywords: str | None = None
    audience_links: list | None = None
    target_chats: list | None = None
    offer_text: str | None = None
    messages_sent: int
    active_dialogs: int
    smart_shield_ok: bool

    model_config = {"from_attributes": True}


def _dispatch(task_name: str, campaign_id: UUID, **kwargs) -> TaskDispatchOut:
    async_result = celery_client.send_task(task_name, args=[str(campaign_id)], kwargs=kwargs)
    return TaskDispatchOut(
        task_id=async_result.id,
        task_name=task_name,
        campaign_id=campaign_id,
    )


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(user_id=payload.user_id, status=CampaignStatus.draft)
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}/knowledge", response_model=CampaignOut)
async def update_knowledge(
    campaign_id: UUID, payload: KnowledgeUpdate, db: AsyncSession = Depends(get_db)
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if payload.knowledge_url is not None:
        campaign.knowledge_url = str(payload.knowledge_url)
    if payload.knowledge_text is not None:
        campaign.knowledge_text = payload.knowledge_text
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/knowledge/parse", response_model=TaskDispatchOut)
async def parse_knowledge(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    """Step 1: enqueue URL/file parsing into campaigns.knowledge_base."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.knowledge_url and not campaign.knowledge_file_path:
        raise HTTPException(status_code=400, detail="No knowledge URL or file path set")

    campaign.status = CampaignStatus.parsing
    await db.flush()

    return _dispatch(
        "workers.parse_knowledge",
        campaign_id,
        source_url=campaign.knowledge_url,
        file_path=campaign.knowledge_file_path,
    )


@router.patch("/{campaign_id}/audience", response_model=CampaignOut)
async def update_audience(
    campaign_id: UUID, payload: AudienceUpdate, db: AsyncSession = Depends(get_db)
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if payload.audience_keywords is not None:
        campaign.audience_keywords = payload.audience_keywords
    if payload.audience_links is not None:
        campaign.audience_links = payload.audience_links
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/audience/parse", response_model=TaskDispatchOut)
async def parse_audience(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    """Step 2: enqueue Telegram group/channel audience parsing."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.audience_links:
        raise HTTPException(status_code=400, detail="No audience links set")

    campaign.status = CampaignStatus.parsing
    await db.flush()
    return _dispatch("workers.parse_audience", campaign_id)


@router.patch("/{campaign_id}/offer", response_model=CampaignOut)
async def update_offer(campaign_id: UUID, payload: OfferUpdate, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.offer_text = payload.offer_text
    campaign.status = CampaignStatus.ready
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/start", response_model=TaskDispatchOut)
async def start_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    """Step 3: enqueue Worker Core (Hydrogram + LLM + Smart-Shield)."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status not in (CampaignStatus.ready, CampaignStatus.paused):
        raise HTTPException(status_code=400, detail="Campaign is not ready to start")
    if not campaign.target_chats:
        raise HTTPException(status_code=400, detail="Parse audience first (target_chats empty)")

    campaign.status = CampaignStatus.running
    await db.flush()
    return _dispatch("workers.run_campaign", campaign_id)


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(user_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.user_id == user_id))
    return list(result.scalars().all())
