"""Per-account baselines. Fixed thresholds are only a fallback for thin history."""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import TransactionStatus
from app.models.transaction import Transaction
from app.models.user import User


@dataclass
class AccountActivity:
    user: User
    now: datetime
    transactions: list[Transaction] = field(default_factory=list)

    def involved(self, tx: Transaction) -> bool:
        return tx.sender_id == self.user.id or tx.receiver_id == self.user.id

    def outbound(self, since: datetime, until: datetime | None = None) -> list[Transaction]:
        end = until or self.now
        return [
            tx
            for tx in self.transactions
            if tx.sender_id == self.user.id and since <= tx.created_at <= end
        ]

    def inbound(self, since: datetime, until: datetime | None = None) -> list[Transaction]:
        end = until or self.now
        return [
            tx
            for tx in self.transactions
            if tx.receiver_id == self.user.id and since <= tx.created_at <= end
        ]

    def prior_outbound_amounts(self) -> list[float]:
        """Sender amounts before the current moment, used for R05."""
        return [
            float(tx.amount)
            for tx in self.transactions
            if tx.sender_id == self.user.id and tx.created_at < self.now
        ]

    def history_before(self, moment: datetime) -> list[Transaction]:
        return [tx for tx in self.transactions if tx.created_at < moment]

    @property
    def thin_history(self) -> bool:
        prior = [tx for tx in self.transactions if tx.created_at < self.now]
        age_days = (self.now - self.user.created_at).total_seconds() / 86400
        return len(prior) < settings.BASELINE_MIN_HISTORY or age_days < settings.NEW_ACCOUNT_DAYS


def load_activity(db: Session, user: User, now: datetime) -> AccountActivity:
    since = now - timedelta(days=settings.BASELINE_DAYS)
    rows = (
        db.execute(
            select(Transaction).where(
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= since,
                Transaction.created_at <= now,
                (Transaction.sender_id == user.id) | (Transaction.receiver_id == user.id),
            )
        )
        .scalars()
        .all()
    )
    return AccountActivity(user=user, now=now, transactions=list(rows))


def load_window(db: Session, since: datetime, until: datetime) -> list[Transaction]:
    return list(
        db.execute(
            select(Transaction).where(
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= since,
                Transaction.created_at <= until,
            )
        )
        .scalars()
        .all()
    )


def median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def robust_z(amount: float, history: list[float]) -> float | None:
    if len(history) < settings.R05_MIN_HISTORY:
        return None
    med = float(statistics.median(history))
    mad = float(statistics.median([abs(value - med) for value in history]))
    if mad == 0:
        if med > 0 and amount >= settings.R05_MEDIAN_MULTIPLIER * med and amount > med:
            return 99.0
        return 0.0
    return abs(amount - med) / mad


def threshold_from_baseline(observed_rate: float | None, fallback: int, multiplier: float) -> int:
    """Use the account's own rate when history exists; otherwise the fixed fallback."""
    if observed_rate is None:
        return fallback
    return max(fallback, int(multiplier * observed_rate))
