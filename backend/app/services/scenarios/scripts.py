"""Scenario scripts among the eight fixed accounts. Every watched transfer goes through execute_transfer."""

import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import LedgerEntryType
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.transaction import TransferRequest
from app.services.reconciliation_service import run_reconciliation
from app.services.scenarios.cast import DEMO_PIN, ensure_cast
from app.services.transfer_service import (
    StepUpRequired,
    TransactionHeld,
    confirm_step_up,
    execute_transfer,
)

LAST_OUTCOME: list[str] = []

Step = tuple[str, str, str, str]


def _pay(db: Session, sender: User, receiver: User, amount: str, remark: str) -> str:
    key = str(uuid.uuid4())
    request = TransferRequest(
        recipient_account_number=receiver.account_number,
        amount=Decimal(amount),
        remark=remark,
        pin=DEMO_PIN,
        idempotency_key=key,
    )
    try:
        transaction = execute_transfer(db, sender, request)
    except StepUpRequired as exc:
        transaction = confirm_step_up(db, sender, exc.challenge_id, exc.code, key)
        LAST_OUTCOME.append(f"STEP_UP_VERIFIED → ALLOW score {exc.risk_score}")
        return transaction.transaction_id
    except TransactionHeld as exc:
        LAST_OUTCOME.append(f"Held for review. {exc.transaction_id}")
        return exc.transaction_id
    return transaction.transaction_id


def _age_activity(db: Session, user_ids: list[int], days: int) -> None:
    when = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.execute(
            select(Transaction).where(
                or_(
                    Transaction.sender_id.in_(user_ids),
                    Transaction.receiver_id.in_(user_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.created_at = when
    db.commit()


def normal_activity(db: Session) -> list[Step]:
    return [
        ("meera", "arjun", "15.00", "Coffee"),
        ("arjun", "meera", "20.00", "Lunch"),
        ("meera", "arjun", "18.00", "Taxi"),
    ]


def legitimate_split_bill(db: Session) -> list[Step]:
    payers = ("rohan", "sara", "dev", "leela", "meera")
    return [(payer, "arjun", "40.00", "Split bill") for payer in payers]


def unusually_large(db: Session) -> list[Step]:
    history = [("kabir", "nia", "20.00", "Usual amount") for _ in range(5)]
    fan = [
        ("kabir", "meera", "20.00", "Fan out"),
        ("kabir", "arjun", "20.00", "Fan out"),
        ("kabir", "rohan", "20.00", "Fan out"),
        ("kabir", "sara", "20.00", "Fan out"),
        ("kabir", "dev", "200.00", "Far above usual"),
    ]
    return [*history, *fan]


def rapid_pass_through(db: Session) -> list[Step]:
    history = [("kabir", "meera", "15.00", "Usual amount") for _ in range(5)]
    inbound = [
        (payer, "kabir", "80.00", "Inbound")
        for payer in ("arjun", "rohan", "sara", "dev", "leela")
    ]
    return [*history, *inbound, ("kabir", "nia", "370.00", "Forward")]


def money_mule_chain(db: Session) -> list[Step]:
    history = [("rohan", "sara", "15.00", "Usual amount") for _ in range(5)]
    chain = [
        ("meera", "kabir", "250.00", "Chain hop"),
        ("kabir", "rohan", "230.00", "Chain hop"),
        ("rohan", "nia", "210.00", "Chain hop"),
    ]
    return [*history, *chain]


def smurfing(db: Session) -> list[Step]:
    cast = ensure_cast(db)
    sender = cast["kabir"]
    prior = db.execute(
        select(Transaction.id).where(Transaction.sender_id == sender.id)
    ).first()
    if prior is None:
        _pay(db, sender, cast["nia"], "10.00", "Earlier outflow")
    _age_activity(db, [sender.id], 2)
    return [("kabir", "nia", "20.00", "Small transfer") for _ in range(8)]


def circular(db: Session) -> list[Step]:
    return [
        ("meera", "rohan", "150.00", "Circle"),
        ("rohan", "sara", "150.00", "Circle"),
        ("sara", "meera", "150.00", "Circle"),
    ]


def _ledger_sum(db: Session, user_id: int) -> Decimal:
    total = db.execute(
        select(
            func.sum(
                case(
                    (LedgerEntry.entry_type == LedgerEntryType.CREDIT, LedgerEntry.amount),
                    else_=-LedgerEntry.amount,
                )
            )
        ).where(LedgerEntry.user_id == user_id)
    ).scalar_one()
    return Decimal(total or 0)


def _shift_wallet(db: Session, user: User, delta: Decimal) -> None:
    """Moves the wallet without a ledger entry, so the next check can see a real mismatch."""
    wallet = db.execute(select(Wallet).where(Wallet.user_id == user.id)).scalar_one()
    wallet.balance = Decimal(wallet.balance) + delta
    db.commit()


def _match_wallet_to_ledger(db: Session, user: User) -> None:
    wallet = db.execute(select(Wallet).where(Wallet.user_id == user.id)).scalar_one()
    wallet.balance = _ledger_sum(db, user.id)
    db.commit()


def play_reconciliation(delay_seconds: float, stopped, status) -> None:
    """Books start matched, then two fixed accounts drift, then the check is clean again."""
    from app.db.session import SessionLocal

    status.total = 4
    status.step = 0
    db = SessionLocal()
    try:
        cast = ensure_cast(db)
        status.step = 1
        status.detail = "Meera pays Arjun through the normal ledger."
        status.last_transaction_id = _pay(db, cast["meera"], cast["arjun"], "12.00", "Reconcile sample")
        report = run_reconciliation(db, triggered_by="scenario")
        status.detail = f"Check 1: books match across {report.accounts_checked} accounts."
    finally:
        db.close()
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    if stopped():
        status.detail = "Stopped after the matching check."
        return

    db = SessionLocal()
    try:
        cast = ensure_cast(db)
        status.step = 2
        _shift_wallet(db, cast["leela"], Decimal("25.00"))
        report = run_reconciliation(db, triggered_by="scenario")
        status.detail = (
            f"Check 2: Leela Nair is 25.00 ST above the ledger. "
            f"{report.discrepancy_count} account out of balance."
        )
    finally:
        db.close()
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    if stopped():
        status.detail = "Stopped while Leela's wallet is above the ledger."
        return

    db = SessionLocal()
    try:
        cast = ensure_cast(db)
        status.step = 3
        _shift_wallet(db, cast["dev"], Decimal("-10.00"))
        report = run_reconciliation(db, triggered_by="scenario")
        status.detail = (
            f"Check 3: Dev Patel is 10.00 ST below the ledger. "
            f"{report.discrepancy_count} accounts out of balance."
        )
    finally:
        db.close()
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    if stopped():
        status.detail = "Stopped while two wallets disagree with the ledger."
        return

    db = SessionLocal()
    try:
        cast = ensure_cast(db)
        status.step = 4
        _match_wallet_to_ledger(db, cast["leela"])
        _match_wallet_to_ledger(db, cast["dev"])
        report = run_reconciliation(db, triggered_by="scenario")
        status.detail = (
            f"Check 4: wallets were put back on the ledger. "
            f"{report.discrepancy_count} accounts out of balance across {report.accounts_checked} checked."
        )
    finally:
        db.close()


def dormant_reactivation(db: Session) -> list[Step]:
    cast = ensure_cast(db)
    sender = cast["kabir"]
    prior = db.execute(
        select(Transaction.id).where(Transaction.sender_id == sender.id)
    ).first()
    if prior is None:
        _pay(db, sender, cast["nia"], "10.00", "Old transfer")
    _age_activity(db, [sender.id], 40)
    return [
        ("kabir", "nia", "25.00", "Back online"),
        ("kabir", "nia", "25.00", "Back online"),
        ("kabir", "nia", "25.00", "Back online"),
    ]


def group_collection(db: Session) -> list[Step]:
    payers = ("rohan", "sara", "dev", "leela", "meera")
    inbound = [(payer, "arjun", "40.00", "Group collection") for payer in payers]
    return [*inbound, ("arjun", "nia", "180.00", "Paid onward")]


def critical_pass_through(db: Session) -> list[Step]:
    """Stacks fan-in, a large onward payment, and a new recipient so a fresh cast can reach critical."""
    history = [("kabir", "meera", "15.00", "Usual amount") for _ in range(5)]
    inbound = [
        (payer, "kabir", "90.00", "Critical inbound")
        for payer in ("arjun", "rohan", "sara", "dev", "leela")
    ]
    return [*history, *inbound, ("kabir", "nia", "430.00", "Critical forward")]


SCENARIOS: dict[str, dict] = {
    "normal": {
        "title": "Normal activity",
        "summary": "Meera and Arjun exchange a few small household payments.",
        "build": normal_activity,
    },
    "split_bill": {
        "title": "Legitimate split bill",
        "summary": "Five established accounts pay Arjun and nobody forwards the money.",
        "build": legitimate_split_bill,
    },
    "large": {
        "title": "Unusually large transfer",
        "summary": "After Kabir's usual payments, he pays five people and the last amount is far above his median.",
        "build": unusually_large,
    },
    "pass_through": {
        "title": "Rapid inbound to outbound",
        "summary": "Kabir receives several payments, then forwards most of them to Nia in one large payment.",
        "build": rapid_pass_through,
    },
    "mule_chain": {
        "title": "Money mule chain",
        "summary": "The same value moves Meera to Kabir to Rohan to Nia, and Rohan's last hop is large for him.",
        "build": money_mule_chain,
    },
    "smurfing": {
        "title": "Smurfing",
        "summary": "Kabir sends eight small payments above an older daily outflow.",
        "build": smurfing,
    },
    "circular": {
        "title": "Circular transfers",
        "summary": "Money moves Meera to Rohan to Sara and back to Meera.",
        "build": circular,
    },
    "dormant": {
        "title": "Dormant reactivation",
        "summary": "Kabir has been quiet for over 30 days, then sends several payments.",
        "build": dormant_reactivation,
    },
    "group_collection": {
        "title": "Group collection paid onward",
        "summary": "Five accounts pay Arjun, who pays Nia. A repeat after a legitimate-group review should score lower.",
        "build": group_collection,
    },
    "critical_pass_through": {
        "title": "Critical pass-through",
        "summary": "A fresh burst into Kabir is forwarded to Nia. The recorded tier is whatever the engine assigns.",
        "build": critical_pass_through,
    },
    "reconciliation": {
        "title": "Reconciliation",
        "summary": "A normal transfer stays balanced, then two wallets drift from the ledger and are corrected.",
        "play": play_reconciliation,
    },
}
