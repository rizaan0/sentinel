from datetime import datetime

from pydantic import BaseModel

from app.models.enums import TransactionStatus


class PlatformStats(BaseModel):
    total_users: int
    total_transactions: int
    total_volume: str
    open_alerts: int
    latest_reconciliation_status: str | None


class PlatformTransaction(BaseModel):
    transaction_id: str
    sender_account_number: str
    sender_name: str
    receiver_account_number: str
    receiver_name: str
    amount: str
    remark: str | None
    status: TransactionStatus
    created_at: datetime


class PaginatedPlatformTransactions(BaseModel):
    items: list[PlatformTransaction]
    total: int
    limit: int
    offset: int
