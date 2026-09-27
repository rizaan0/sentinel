"""
Transfer/payment core: recipient search and the transfer execution pipeline.

Architecture Rule: business logic lives only in backend services. This is
the "Transaction Service" from the architecture diagram; it runs Transaction
Validation (recipient exists, PIN verification, wallet balance) before any
balance is touched, and produces the Transaction record used for receipts
and, from Phase 3 onward, ledger entries.
"""
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import TRANSACTION_COMPLETED, TransactionCompletedEvent, event_bus
from app.models.amount_hold import AmountHold
from app.models.enums import HoldStatus, TransactionStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.transaction import TransferRequest
from app.services.ledger_service import record_transfer
from app.services.pin_service import (
    InvalidPinError,  # noqa: F401  (re-exported for API layer error mapping)
    PinLockedError,  # noqa: F401
    PinNotSetError,  # noqa: F401
    verify_transaction_pin,
)
from app.services.realtime import publish_event


class RecipientNotFoundError(Exception):
    pass


class SelfTransferError(Exception):
    pass


class InsufficientBalanceError(Exception):
    pass


class FundsOnHoldError(Exception):
    pass


def active_hold_total(db: Session, user_id: int) -> Decimal:
    """Sum of active holds. Expired holds are closed the first time they are read."""
    now = datetime.now(UTC)
    holds = (
        db.execute(
            select(AmountHold).where(
                AmountHold.user_id == user_id,
                AmountHold.status == HoldStatus.ACTIVE,
            )
        )
        .scalars()
        .all()
    )
    total = Decimal("0")
    changed = False
    for hold in holds:
        expires = hold.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= now:
            hold.status = HoldStatus.EXPIRED
            changed = True
            continue
        total += Decimal(hold.amount)
    if changed:
        db.flush()
    return total


def search_recipient(db: Session, account_number: str, exclude_user_id: int) -> User | None:
    user = db.execute(
        select(User).where(User.account_number == account_number)
    ).scalar_one_or_none()
    if user is None or user.id == exclude_user_id or not user.is_active:
        return None
    return user


def search_recipients(
    db: Session,
    query: str,
    exclude_user_id: int,
    *,
    limit: int = 10,
) -> list[User]:
    """
    Recipient discovery: exact account, account prefix, or case-insensitive
    name match. Never exposes email. Caps results for a clean picker UX.
    """
    q = query.strip()
    if not q:
        return []

    digits_only = q.isdigit()
    if digits_only:
        exact = search_recipient(db, q, exclude_user_id)
        if exact is not None and len(q) >= 12:
            return [exact]

        rows = (
            db.execute(
                select(User)
                .where(
                    User.is_active.is_(True),
                    User.id != exclude_user_id,
                    User.account_number.startswith(q),
                )
                .order_by(User.full_name)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return list(rows)

    pattern = f"%{q}%"
    rows = (
        db.execute(
            select(User)
            .where(
                User.is_active.is_(True),
                User.id != exclude_user_id,
                User.full_name.ilike(pattern),
            )
            .order_by(User.full_name)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(rows)


def execute_transfer(db: Session, sender: User, payload: TransferRequest) -> Transaction:
    # --- Transaction Validation: Recipient Exists ---
    receiver = db.execute(
        select(User).where(User.account_number == payload.recipient_account_number)
    ).scalar_one_or_none()
    if receiver is None or not receiver.is_active:
        raise RecipientNotFoundError(
            f"No active account found for {payload.recipient_account_number}"
        )
    if receiver.id == sender.id:
        raise SelfTransferError("Cannot transfer money to your own account")

    # --- Transaction Validation: PIN Verification ---
    # Re-fetch sender within this session to ensure pin_credential is loaded.
    verify_transaction_pin(db, sender, payload.pin)

    # --- Transaction Validation: Wallet Balance (locked to prevent races) ---
    # Lock both wallets in a consistent order (by user id) to avoid deadlocks
    # when two concurrent transfers involve the same pair of accounts.
    first_id, second_id = sorted([sender.id, receiver.id])
    locked_wallets = (
        db.execute(
            select(Wallet)
            .where(Wallet.user_id.in_([first_id, second_id]))
            .order_by(Wallet.user_id)
            .with_for_update()
        )
        .scalars()
        .all()
    )
    wallets_by_user = {w.user_id: w for w in locked_wallets}
    sender_wallet = wallets_by_user[sender.id]
    receiver_wallet = wallets_by_user[receiver.id]

    amount: Decimal = payload.amount
    held = active_hold_total(db, sender.id)
    available = sender_wallet.balance - held
    if held > 0 and amount > available:
        raise FundsOnHoldError(
            f"{held} ST is on hold after a risk review, so only {available} ST can be sent. "
            "You can still receive money. Open Home for the reason and how to respond."
        )
    if sender_wallet.balance < amount:
        raise InsufficientBalanceError("Insufficient balance for this transfer")

    # --- Ledger Service: source of financial truth ---
    # Transaction Service -> Transaction Validation (above) -> Ledger Service
    # -> PostgreSQL commit -> Transaction Completed Event.
    transaction = Transaction(
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=amount,
        remark=payload.remark,
        status=TransactionStatus.COMPLETED,
    )
    db.add(transaction)
    db.flush()  # assign transaction.id so ledger entries can reference it

    record_transfer(db, sender_wallet, receiver_wallet, transaction, amount)

    db.commit()
    db.refresh(transaction)

    # Only after PostgreSQL confirms the commit succeeded does the canonical
    # domain event fire, fanned out in parallel to Monitoring (Phase 4) and
    # to Redis Pub/Sub for the live admin feed (Phase 5) - never before, so
    # a rolled-back transaction can never produce a fraud alert or a
    # live-feed entry.
    event_bus.publish(
        TRANSACTION_COMPLETED,
        TransactionCompletedEvent(
            transaction_id=transaction.transaction_id,
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=amount,
        ),
    )
    publish_event(
        "transaction",
        {
            "transaction_id": transaction.transaction_id,
            "sender_account_number": sender.account_number,
            "sender_name": sender.full_name,
            "receiver_account_number": receiver.account_number,
            "receiver_name": receiver.full_name,
            "amount": str(amount),
            "created_at": transaction.created_at,
        },
    )

    return transaction


def get_transaction_for_user(db: Session, user: User, transaction_id: str) -> Transaction | None:
    transaction = db.execute(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).scalar_one_or_none()
    if transaction is None:
        return None
    if transaction.sender_id != user.id and transaction.receiver_id != user.id:
        return None
    return transaction


def list_transactions_for_user(
    db: Session, user: User, limit: int, offset: int
) -> tuple[list[Transaction], int]:
    filter_clause = (Transaction.sender_id == user.id) | (Transaction.receiver_id == user.id)
    base_query = select(Transaction).where(filter_clause)

    total = db.execute(
        select(func.count()).select_from(Transaction).where(filter_clause)
    ).scalar_one()
    items = (
        db.execute(
            base_query.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return items, total
