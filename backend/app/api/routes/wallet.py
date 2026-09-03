"""Adsgram wallet API (in-memory)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.store.memory import store

router = APIRouter()


class BalanceOut(BaseModel):
    user_id: str
    balance: int


class TopUpRequest(BaseModel):
    user_id: str
    amount: int = Field(gt=0, le=1_000_000)


@router.get("/balance", response_model=BalanceOut)
async def get_balance(user_id: str):
    user = store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return BalanceOut(user_id=user_id, balance=user.balance)


@router.post("/topup-test", response_model=BalanceOut)
async def topup_test(payload: TopUpRequest):
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=403, detail="Test top-up only in development")

    user = store.get_user(payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.balance += payload.amount
    store.add_transaction(payload.user_id, payload.amount, "topup", "Тестовое пополнение")
    return BalanceOut(user_id=payload.user_id, balance=user.balance)


@router.get("/transactions")
async def list_transactions(user_id: str):
    rows = store.list_transactions(user_id)
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "kind": t.kind,
            "description": t.description,
            "reference_id": t.reference_id,
            "created_at": t.created_at,
        }
        for t in rows
    ]
