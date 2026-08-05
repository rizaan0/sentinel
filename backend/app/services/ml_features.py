"""
Online feature extraction for the ML Anomaly Detector - mirrors
ml/feature_engineering.py (see that module for the canonical feature list
and semantics). This computes the same features per-transaction via SQL,
at inference time, right after a transaction commits.
"""
import statistics
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TransactionStatus
from app.models.transaction import Transaction

FEATURE_COLUMNS = [
    "amount",
    "sender_avg_amount_30d",
    "sender_std_amount_30d",
    "sender_txn_count_1h",
    "sender_txn_count_24h",
    "unique_receivers_24h",
    "amount_to_avg_ratio",
    "hour_of_day",
    "is_new_receiver",
]


def extract_features(db: Session, transaction: Transaction) -> list[float]:
    now = transaction.created_at
    sender_id = transaction.sender_id

    history = (
        db.execute(
            select(Transaction).where(
                Transaction.sender_id == sender_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= now - timedelta(days=30),
                Transaction.created_at < now,
            )
        )
        .scalars()
        .all()
    )

    amounts = [float(t.amount) for t in history]
    avg = statistics.mean(amounts) if amounts else 0.0
    std = statistics.pstdev(amounts) if len(amounts) > 1 else 0.0

    count_1h = sum(1 for t in history if now - t.created_at <= timedelta(hours=1))
    count_24h = sum(1 for t in history if now - t.created_at <= timedelta(hours=24))
    receivers_24h = {
        t.receiver_id for t in history if now - t.created_at <= timedelta(hours=24)
    }
    is_new_receiver = not any(t.receiver_id == transaction.receiver_id for t in history)

    amount = float(transaction.amount)
    ratio = (amount / (avg + 1e-6)) if avg > 0 else 1.0

    return [
        amount,
        avg,
        std,
        float(count_1h),
        float(count_24h),
        float(len(receivers_24h)),
        ratio,
        float(now.hour),
        1.0 if is_new_receiver else 0.0,
    ]
