"""
Transfer/payment core: recipient search and the transfer execution pipeline.

Architecture Rule: business logic lives only in backend services. This is
the "Transaction Service" from the architecture diagram; it runs Transaction
Validation (recipient exists, PIN verification, wallet balance) before any
balance is touched, and produces the Transaction record used for receipts
and, from Phase 3 onward, ledger entries.
"""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import TRANSACTION_COMPLETED, TransactionCompletedEvent, event_bus
from app.models.enums import TransactionStatus
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


def search_recipient(db: Session, account_number: str, exclude_user_id: int) -> User | None:
    user = db.execute(
        select(User).where(User.account_number == account_number)
    ).scalar_one_or_none()
    if user is None or user.id == exclude_user_id or not user.is_active:
        return None
    return user


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
