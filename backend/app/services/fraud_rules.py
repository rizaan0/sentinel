"""
Rule Engine: behavioral fraud detection rules. Each rule inspects a
transaction plus recent activity and returns a RuleResult only if it
triggers. Fraud is never manually marked here - it emerges from behavior
(per idea.md): rapid repeated transfers, circular fund flow, unusually
large transfers, and bursts of small transactions.
"""
import statistics
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import TransactionStatus
from app.models.transaction import Transaction


@dataclass(frozen=True)
class RuleResult:
    rule_name: str
    explanation: str
    risk_weight: int


def _sender_history(db: Session, sender_id: int, since) -> list[Transaction]:
    return (
        db.execute(
            select(Transaction)
            .where(
                Transaction.sender_id == sender_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= since,
            )
            .order_by(Transaction.created_at.desc())
        )
        .scalars()
        .all()
    )


def rapid_repeated_transfers(db: Session, transaction: Transaction) -> RuleResult | None:
    """Repeated transfers between the same two accounts within a short window."""
    window_start = transaction.created_at - timedelta(
        seconds=settings.RAPID_REPEAT_WINDOW_SECONDS
    )
    count = db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.sender_id == transaction.sender_id,
            Transaction.receiver_id == transaction.receiver_id,
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.created_at >= window_start,
            Transaction.created_at <= transaction.created_at,
        )
    ).scalar_one()

    if count >= settings.RAPID_REPEAT_MIN_COUNT:
        return RuleResult(
            rule_name="rapid_repeated_transfers",
            explanation=(
                f"{count} transfers from account {transaction.sender.account_number} to "
                f"{transaction.receiver.account_number} within "
                f"{settings.RAPID_REPEAT_WINDOW_SECONDS} seconds."
            ),
            risk_weight=30,
        )
    return None


def circular_fund_flow(db: Session, transaction: Transaction) -> RuleResult | None:
    """Detects funds looping back to the sender through other accounts."""
    window_start = transaction.created_at - timedelta(
        minutes=settings.CIRCULAR_FLOW_WINDOW_MINUTES
    )
    recent = (
        db.execute(
            select(Transaction).where(
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= window_start,
                Transaction.created_at <= transaction.created_at,
            )
        )
        .scalars()
        .all()
    )

    graph: dict[int, set[int]] = {}
    for tx in recent:
        graph.setdefault(tx.sender_id, set()).add(tx.receiver_id)

    origin = transaction.sender_id
    visited = {origin}

    def dfs(node: int, depth: int) -> int | None:
        if depth > settings.CIRCULAR_FLOW_MAX_HOPS:
            return None
        for neighbor in graph.get(node, set()):
            if neighbor == origin and depth >= 1:
                return depth
            if neighbor in visited:
                continue
            visited.add(neighbor)
            hops = dfs(neighbor, depth + 1)
            if hops is not None:
                return hops
        return None

    hops = dfs(origin, 1)
    if hops is not None:
        return RuleResult(
            rule_name="circular_fund_flow",
            explanation=(
                f"Funds sent from account {transaction.sender.account_number} circulated back "
                f"to the same account through {hops} hop(s) within "
                f"{settings.CIRCULAR_FLOW_WINDOW_MINUTES} minutes."
            ),
            risk_weight=40,
        )
    return None


def unusually_large_transfer(db: Session, transaction: Transaction) -> RuleResult | None:
    """Compares the transfer amount to the sender's own historical pattern."""
    lookback_start = transaction.created_at - timedelta(days=365)
    history = [
        t
        for t in _sender_history(db, transaction.sender_id, lookback_start)
        if t.id != transaction.id
    ]
    if len(history) < settings.LARGE_TRANSFER_MIN_HISTORY:
        return None

    amounts = [float(t.amount) for t in history]
    mean = statistics.mean(amounts)
    stdev = statistics.pstdev(amounts) if len(amounts) > 1 else 0.0
    threshold = mean + settings.LARGE_TRANSFER_STDDEV_MULTIPLIER * stdev

    amount = float(transaction.amount)
    if amount > threshold and amount > mean:
        return RuleResult(
            rule_name="unusually_large_transfer",
            explanation=(
                f"Transfer amount {transaction.amount} ST is significantly higher than the "
                f"sender's historical average of {mean:.2f} ST over {len(amounts)} past transfers."
            ),
            risk_weight=25,
        )
    return None


def burst_of_small_transactions(db: Session, transaction: Transaction) -> RuleResult | None:
    """Many small transactions sent in a short period."""
    if float(transaction.amount) > settings.BURST_MAX_AMOUNT:
        return None

    window_start = transaction.created_at - timedelta(minutes=settings.BURST_WINDOW_MINUTES)
    count = db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.sender_id == transaction.sender_id,
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.amount <= settings.BURST_MAX_AMOUNT,
            Transaction.created_at >= window_start,
            Transaction.created_at <= transaction.created_at,
        )
    ).scalar_one()

    if count >= settings.BURST_MIN_COUNT:
        return RuleResult(
            rule_name="burst_of_small_transactions",
            explanation=(
                f"{count} small transactions (<= {settings.BURST_MAX_AMOUNT} ST) sent from "
                f"account {transaction.sender.account_number} within "
                f"{settings.BURST_WINDOW_MINUTES} minutes."
            ),
            risk_weight=20,
        )
    return None


ALL_RULES = [
    rapid_repeated_transfers,
    circular_fund_flow,
    unusually_large_transfer,
    burst_of_small_transactions,
]
