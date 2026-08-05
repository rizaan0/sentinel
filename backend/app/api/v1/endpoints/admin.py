"""
Admin-only aggregation endpoints backing the Admin Dashboard overview and
the platform-wide (not per-user) transaction feed.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.enums import AlertStatus, TransactionStatus
from app.models.fraud_alert import FraudAlert
from app.models.reconciliation_report import ReconciliationReport
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.admin import PaginatedPlatformTransactions, PlatformStats, PlatformTransaction

router = APIRouter()


@router.get("/stats", response_model=PlatformStats)
def get_platform_stats(
    _admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> PlatformStats:
    total_users = db.execute(select(func.count()).select_from(User)).scalar_one()
    total_transactions = db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.status == TransactionStatus.COMPLETED)
    ).scalar_one()
    total_volume = db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.status == TransactionStatus.COMPLETED
        )
    ).scalar_one()
    open_alerts = db.execute(
        select(func.count())
        .select_from(FraudAlert)
        .where(FraudAlert.status == AlertStatus.OPEN)
    ).scalar_one()
    latest_report = db.execute(
        select(ReconciliationReport).order_by(ReconciliationReport.created_at.desc()).limit(1)
    ).scalar_one_or_none()

    return PlatformStats(
        total_users=total_users,
        total_transactions=total_transactions,
        total_volume=str(total_volume),
        open_alerts=open_alerts,
        latest_reconciliation_status=latest_report.status.value if latest_report else None,
    )


@router.get("/transactions", response_model=PaginatedPlatformTransactions)
def list_all_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaginatedPlatformTransactions:
    """Every transaction on the platform (not scoped to a single user)."""
    total = db.execute(select(func.count()).select_from(Transaction)).scalar_one()
    rows = (
        db.execute(
            select(Transaction)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    items = [
        PlatformTransaction(
            transaction_id=tx.transaction_id,
            sender_account_number=tx.sender.account_number,
            sender_name=tx.sender.full_name,
            receiver_account_number=tx.receiver.account_number,
            receiver_name=tx.receiver.full_name,
            amount=str(tx.amount),
            remark=tx.remark,
            status=tx.status,
            created_at=tx.created_at,
        )
        for tx in rows
    ]
    return PaginatedPlatformTransactions(items=items, total=total, limit=limit, offset=offset)
