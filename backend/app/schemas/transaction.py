from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import TransactionStatus


class TransferRequest(BaseModel):
    recipient_account_number: str = Field(min_length=1, max_length=20)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    remark: str | None = Field(default=None, max_length=280)
    pin: str = Field(min_length=4, max_length=6)
    idempotency_key: str | None = Field(default=None, max_length=64)


class StepUpConfirm(BaseModel):
    challenge_id: str
    code: str = Field(min_length=6, max_length=6)
    idempotency_key: str = Field(min_length=1, max_length=64)


class TransactionReceipt(BaseModel):
    transaction_id: str
    sender_account_number: str
    sender_name: str
    receiver_account_number: str
    receiver_name: str
    amount: Decimal
    remark: str | None
    status: TransactionStatus
    created_at: datetime
    direction: Literal["sent", "received"]
    balance_after: Decimal


class TransactionSummary(BaseModel):
    transaction_id: str
    counterparty_account_number: str
    counterparty_name: str
    amount: Decimal
    remark: str | None
    status: TransactionStatus
    created_at: datetime
    direction: Literal["sent", "received"]


class PaginatedTransactions(BaseModel):
    items: list[TransactionSummary]
    total: int
    limit: int
    offset: int
