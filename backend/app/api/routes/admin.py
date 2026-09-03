"""Admin/setup endpoints for E2E and local development."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import is_admin_api_enabled
from app.core.database import get_db
from app.models import AccountStatus, Proxy, TelegramAccount, User

router = APIRouter()


def _require_dev() -> None:
    if not is_admin_api_enabled():
        raise HTTPException(
            status_code=403,
            detail="Admin endpoints require ENVIRONMENT=development and ENABLE_ADMIN_API=true",
        )


class UserCreate(BaseModel):
    email: EmailStr
    hashed_password: str = "e2e-test-not-used"


class UserOut(BaseModel):
    id: UUID
    email: str
    is_active: bool

    model_config = {"from_attributes": True}


class ProxyCreate(BaseModel):
    host: str
    port: int
    protocol: str = "socks5"
    username: str | None = None
    password: str | None = None
    is_active: bool = True


class ProxyOut(BaseModel):
    id: UUID
    host: str
    port: int
    protocol: str
    username: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class TelegramAccountCreate(BaseModel):
    session_path: str
    phone: str | None = None
    proxy_id: UUID | None = None
    status: AccountStatus = AccountStatus.reserved
    daily_limit: int = 40


class TelegramAccountOut(BaseModel):
    id: UUID
    phone: str | None
    session_path: str
    status: AccountStatus
    proxy_id: UUID | None
    daily_sent_count: int
    daily_limit: int

    model_config = {"from_attributes": True}


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    _require_dev()
    user = User(email=payload.email, hashed_password=payload.hashed_password)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)):
    _require_dev()
    result = await db.execute(select(User))
    return list(result.scalars().all())


@router.post("/proxies", response_model=ProxyOut, status_code=status.HTTP_201_CREATED)
async def create_proxy(payload: ProxyCreate, db: AsyncSession = Depends(get_db)):
    _require_dev()
    proxy = Proxy(
        host=payload.host,
        port=payload.port,
        protocol=payload.protocol,
        username=payload.username,
        password=payload.password,
        is_active=payload.is_active,
    )
    db.add(proxy)
    await db.flush()
    await db.refresh(proxy)
    return proxy


@router.get("/proxies", response_model=list[ProxyOut])
async def list_proxies(db: AsyncSession = Depends(get_db)):
    _require_dev()
    result = await db.execute(select(Proxy))
    return list(result.scalars().all())


@router.post("/telegram-accounts", response_model=TelegramAccountOut, status_code=status.HTTP_201_CREATED)
async def create_telegram_account(payload: TelegramAccountCreate, db: AsyncSession = Depends(get_db)):
    _require_dev()
    if payload.proxy_id:
        proxy = await db.get(Proxy, payload.proxy_id)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")

    account = TelegramAccount(
        phone=payload.phone,
        session_path=payload.session_path,
        status=payload.status,
        proxy_id=payload.proxy_id,
        daily_limit=payload.daily_limit,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.get("/telegram-accounts", response_model=list[TelegramAccountOut])
async def list_telegram_accounts(db: AsyncSession = Depends(get_db)):
    _require_dev()
    result = await db.execute(select(TelegramAccount))
    return list(result.scalars().all())
