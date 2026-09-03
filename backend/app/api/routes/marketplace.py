"""Adsgram marketplace API (in-memory store)."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.channel_connect import ChannelConnectError, connect_channel
from app.services.telegram_bot import resolve_bot_username
from app.services import marketplace_memory as svc
from app.store.memory import DEFAULT_PRICING, store

router = APIRouter()


class PricingOption(BaseModel):
    duration_hours: int
    label: str
    price: int


class ChannelOut(BaseModel):
    id: str
    title: str
    username: str | None
    subscribers_count: int
    rating: float
    completed_orders: int
    total_orders: int
    pricing: list[PricingOption]
    stats: dict | None = None


class ChannelRegister(BaseModel):
    telegram_chat_id: str
    chat_type: str = "channel"
    title: str
    username: str | None = None
    owner_telegram_id: str
    subscribers_count: int = 0
    can_post: bool = False


class ChannelConnectIn(BaseModel):
    user_id: str
    channel_username: str = Field(min_length=1, max_length=255)


class ConnectInfoOut(BaseModel):
    bot_username: str | None
    add_bot_url: str | None


class AdOrderCreate(BaseModel):
    advertiser_user_id: str
    channel_id: str
    post_text: str = Field(min_length=1, max_length=4096)
    duration_hours: int = Field(ge=1, le=720)
    post_media: dict | None = None


class AdOrderOut(BaseModel):
    id: str
    channel_id: str
    advertiser_user_id: str
    post_text: str
    duration_hours: int
    price: int
    status: str
    published_message_id: int | None = None
    published_at: str | None = None
    expires_at: str | None = None


def _channel_out(ch) -> ChannelOut:
    return ChannelOut(
        id=ch.id,
        title=ch.title,
        username=ch.username,
        subscribers_count=ch.subscribers_count,
        rating=ch.rating,
        completed_orders=ch.completed_orders,
        total_orders=ch.total_orders,
        pricing=[PricingOption(**p) for p in ch.pricing],
        stats=ch.stats,
    )


def _order_out(o) -> AdOrderOut:
    return AdOrderOut(
        id=o.id,
        channel_id=o.channel_id,
        advertiser_user_id=o.advertiser_user_id,
        post_text=o.post_text,
        duration_hours=o.duration_hours,
        price=o.price,
        status=o.status,
        published_message_id=o.published_message_id,
        published_at=o.published_at,
        expires_at=o.expires_at,
    )


@router.get("/channels", response_model=list[ChannelOut])
async def list_channels():
    return [_channel_out(c) for c in store.list_channels()]


@router.get("/channels/{channel_id}", response_model=ChannelOut)
async def get_channel(channel_id: str):
    ch = store.get_channel(channel_id)
    if not ch or not ch.is_active:
        raise HTTPException(status_code=404, detail="Channel not found")
    return _channel_out(ch)


@router.get("/channels/connect-info", response_model=ConnectInfoOut)
async def channel_connect_info():
    bot_username = await resolve_bot_username()
    add_bot_url = None
    if bot_username:
        add_bot_url = f"https://t.me/{bot_username}?startchannel&admin=post_messages"
    return ConnectInfoOut(bot_username=bot_username, add_bot_url=add_bot_url)


@router.get("/channels/mine", response_model=list[ChannelOut])
async def list_my_channels(user_id: str):
    user = store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    channels = store.list_channels_by_owner(user.telegram_id)
    return [_channel_out(c) for c in channels]


@router.post("/channels/connect", response_model=ChannelOut)
async def connect_channel_endpoint(payload: ChannelConnectIn):
    user = store.get_user(payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        ch = await connect_channel(user.telegram_id, payload.channel_username)
    except ChannelConnectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _channel_out(ch)


@router.post("/channels/register", response_model=ChannelOut)
async def register_channel_endpoint(payload: ChannelRegister):
    ch = store.register_channel(
        telegram_chat_id=payload.telegram_chat_id,
        chat_type=payload.chat_type,
        title=payload.title,
        username=payload.username,
        owner_telegram_id=payload.owner_telegram_id,
        subscribers_count=payload.subscribers_count,
        can_post=payload.can_post,
    )
    return _channel_out(ch)


@router.post("/orders", response_model=AdOrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(payload: AdOrderCreate):
    try:
        order = svc.create_order(
            advertiser_user_id=payload.advertiser_user_id,
            channel_id=payload.channel_id,
            post_text=payload.post_text,
            duration_hours=payload.duration_hours,
            post_media=payload.post_media,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _order_out(order)


@router.post("/orders/{order_id}/pay", response_model=AdOrderOut)
async def pay_order(order_id: str, advertiser_user_id: str):
    try:
        order = await svc.pay_order(order_id, advertiser_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _order_out(order)


@router.post("/orders/{order_id}/approve", response_model=AdOrderOut)
async def approve_order(order_id: str, owner_telegram_id: str):
    try:
        order = await svc.approve_order(order_id, owner_telegram_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _order_out(order)


@router.post("/orders/{order_id}/reject", response_model=AdOrderOut)
async def reject_order(order_id: str, owner_telegram_id: str):
    try:
        order = svc.reject_order(order_id, owner_telegram_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _order_out(order)


@router.get("/orders", response_model=list[AdOrderOut])
async def list_orders(user_id: str):
    return [_order_out(o) for o in svc.list_orders_for_user(user_id)]
