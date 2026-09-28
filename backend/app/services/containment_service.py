"""Quarantine tainted funds along the traced chain. Restrict only the confirmed subject."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account_restriction import AccountRestriction
from app.models.amount_hold import AmountHold
from app.models.enums import HoldKind, HoldStatus, TransactionStatus
from app.models.fraud_alert import FraudAlert
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.services.case_events import record_case_event
from app.services.ledger_service import record_transfer


def trace_and_quarantine(db: Session, alert: FraudAlert, actor: str) -> None:
    flagged = alert.transaction
    if flagged is None:
        return
    basis = Decimal(str(flagged.amount))
    for signal in alert.signals or []:
        hold_basis = (signal.get("hold_basis") or 0) if signal.get("score_contribution", 0) > 0 else 0
        if hold_basis:
            basis = Decimal(str(hold_basis))
            break
    window_end = flagged.created_at + timedelta(minutes=settings.R10_WINDOW_MINUTES)
    # Hop 0 delivers the flagged amount to the receiver.
    queue = [(flagged.receiver_id, flagged.created_at, basis)]
    seen = {flagged.id}
    hops = 0
    while queue and hops < 4:
        hops += 1
        nxt = []
        for account_id, arrived, tainted in queue:
            if tainted < 1:
                continue
            _quarantine(db, alert, account_id, tainted, actor)
            outgoing = db.execute(
                select(Transaction).where(
                    Transaction.sender_id == account_id,
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= arrived,
                    Transaction.created_at <= window_end,
                )
            ).scalars().all()
            for transfer in outgoing:
                if transfer.id in seen:
                    continue
                seen.add(transfer.id)
                carried = min(tainted, Decimal(transfer.amount))
                if carried < 1:
                    continue
                nxt.append((transfer.receiver_id, transfer.created_at, carried))
        queue = nxt
    subject_id = alert.subject_user_id or alert.user_id
    already = db.execute(
        select(AccountRestriction).where(
            AccountRestriction.user_id == subject_id,
            AccountRestriction.active.is_(True),
        )
    ).scalar_one_or_none()
    if already is None:
        db.add(
            AccountRestriction(
                user_id=subject_id,
                alert_id=alert.id,
                scope="outgoing",
                active=True,
                reason="Confirmed fraud. Outgoing transfers are restricted. Incoming transfers still work.",
            )
        )
        record_case_event(
            db,
            alert.id,
            "restriction",
            actor,
            {"user_id": subject_id, "scope": "outgoing"},
        )


def _quarantine(db: Session, alert: FraudAlert, user_id: int, tainted: Decimal, actor: str) -> None:
    wallet = db.execute(select(Wallet).where(Wallet.user_id == user_id)).scalar_one_or_none()
    balance = Decimal(wallet.balance) if wallet is not None else Decimal("0")
    amount = min(tainted, balance)
    if amount < 1:
        return
    existing = db.execute(
        select(AmountHold).where(
            AmountHold.alert_id == alert.id,
            AmountHold.user_id == user_id,
            AmountHold.kind == HoldKind.QUARANTINE.value,
            AmountHold.status.in_([HoldStatus.ACTIVE, HoldStatus.CONFIRMED]),
        )
    ).scalars().first()
    if existing is not None:
        return
    from datetime import UTC, datetime, timedelta as td

    now = datetime.now(UTC)
    db.add(
        AmountHold(
            user_id=user_id,
            alert_id=alert.id,
            amount=amount,
            status=HoldStatus.ACTIVE,
            kind=HoldKind.QUARANTINE.value,
            reason_codes=["quarantine"],
            expires_at=now + td(days=3650),
            explanation_due_at=now + td(days=7),
            narrative="Quarantine of funds traced from a confirmed case. Incoming transfers still work.",
        )
    )
    record_case_event(
        db,
        alert.id,
        "quarantine",
        actor,
        {"user_id": user_id, "amount": str(amount)},
    )


def settle_held(db: Session, alert: FraudAlert, actor: str) -> None:
    transaction = alert.transaction
    if transaction is None or transaction.status != TransactionStatus.HELD:
        return
    sender_wallet = db.execute(select(Wallet).where(Wallet.user_id == transaction.sender_id)).scalar_one()
    receiver_wallet = db.execute(select(Wallet).where(Wallet.user_id == transaction.receiver_id)).scalar_one()
    reservation = db.execute(
        select(AmountHold).where(
            AmountHold.transaction_id == transaction.id,
            AmountHold.kind == HoldKind.RESERVATION.value,
            AmountHold.status == HoldStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if reservation is not None:
        reservation.status = HoldStatus.RELEASED
    record_transfer(db, sender_wallet, receiver_wallet, transaction, Decimal(transaction.amount))
    transaction.status = TransactionStatus.COMPLETED
    record_case_event(db, alert.id, "hold_released", actor, {"transaction_id": transaction.transaction_id})


def reject_held(db: Session, alert: FraudAlert, actor: str) -> None:
    transaction = alert.transaction
    if transaction is None or transaction.status != TransactionStatus.HELD:
        return
    reservation = db.execute(
        select(AmountHold).where(
            AmountHold.transaction_id == transaction.id,
            AmountHold.kind == HoldKind.RESERVATION.value,
            AmountHold.status == HoldStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if reservation is not None:
        reservation.status = HoldStatus.RELEASED
    transaction.status = TransactionStatus.REJECTED
    record_case_event(db, alert.id, "hold_confirmed", actor, {"transaction_id": transaction.transaction_id})
