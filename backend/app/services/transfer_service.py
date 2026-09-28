"""
Transfer/payment core: recipient search and the transfer execution pipeline.

Architecture Rule: business logic lives only in backend services. This is
the "Transaction Service" from the architecture diagram; it runs Transaction
Validation (recipient exists, PIN verification, wallet balance) before any
balance is touched, and produces the Transaction record used for receipts
and, from Phase 3 onward, ledger entries.
"""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import TRANSACTION_COMPLETED, TransactionCompletedEvent, event_bus
from app.models.account_restriction import AccountRestriction
from app.models.amount_hold import AmountHold
from app.models.enums import HoldKind, HoldStatus, TransactionStatus
from app.models.step_up_challenge import StepUpChallenge
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.transaction import TransferRequest
from app.services.ledger_service import record_transfer
from app.services.risk.decision import ACTION_HOLD, ACTION_STEP_UP
from app.services.risk.engine import evaluate
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


class AccountRestrictedError(Exception):
    pass


class IdempotencyConflict(Exception):
    pass


class StepUpRequired(Exception):
    def __init__(self, challenge_id: str, code: str | None, reasons: list[str], risk_score: int):
        self.challenge_id = challenge_id
        self.code = code
        self.reasons = reasons
        self.risk_score = risk_score
        super().__init__("This transfer needs confirmation")


class TransactionHeld(Exception):
    def __init__(self, transaction_id: str, reasons: list[str]):
        self.transaction_id = transaction_id
        self.reasons = reasons
        super().__init__("Held for review")


class ChallengeRejected(Exception):
    pass


def active_hold_total(db: Session, user_id: int) -> Decimal:
    """Money that cannot be sent. Confirmed holds stay unavailable. Only risk holds expire."""
    now = datetime.now(UTC)
    holds = (
        db.execute(
            select(AmountHold).where(
                AmountHold.user_id == user_id,
                AmountHold.status.in_([HoldStatus.ACTIVE, HoldStatus.CONFIRMED]),
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
        if hold.status == HoldStatus.ACTIVE and hold.kind == HoldKind.RISK.value and expires <= now:
            hold.status = HoldStatus.EXPIRED
            changed = True
            continue
        total += Decimal(hold.amount)
    if changed:
        db.flush()
    return total


def canonical_account_number(value: str) -> str:
    """Stored account numbers are 12 digits. Display grouping is not part of the value."""
    stripped = value.strip()
    digits = "".join(ch for ch in stripped if ch.isdigit())
    if digits and all(ch.isdigit() or ch in " -" for ch in stripped):
        return digits
    return stripped


def search_recipient(db: Session, account_number: str, exclude_user_id: int) -> User | None:
    user = db.execute(
        select(User).where(User.account_number == canonical_account_number(account_number))
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
    q = canonical_account_number(query)
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
        select(User).where(User.account_number == canonical_account_number(payload.recipient_account_number))
    ).scalar_one_or_none()
    if receiver is None or not receiver.is_active:
        raise RecipientNotFoundError(
            f"No active account found for {payload.recipient_account_number}"
        )
    if receiver.id == sender.id:
        raise SelfTransferError("Cannot transfer money to your own account")

    existing = _existing_for_key(db, sender, receiver, payload)
    if existing is not None:
        return existing

    if (
        db.execute(
            select(AccountRestriction.id).where(
                AccountRestriction.user_id == sender.id,
                AccountRestriction.active.is_(True),
                AccountRestriction.scope == "outgoing",
            )
        ).scalar_one_or_none()
        is not None
    ):
        raise AccountRestrictedError(
            "Outgoing transfers from this account are restricted while a confirmed case is open. "
            "You can still receive money."
        )

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
    key = payload.idempotency_key or str(uuid.uuid4())
    transaction = Transaction(
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=amount,
        remark=payload.remark,
        status=TransactionStatus.COMPLETED,
        idempotency_key=key,
    )
    db.add(transaction)
    db.flush()

    record_transfer(db, sender_wallet, receiver_wallet, transaction, amount)
    db.flush()
    result = evaluate(db, transaction)
    action = result["action"] if result else "allow"
    if action in {ACTION_STEP_UP, ACTION_HOLD}:
        reasons = _reasons(result)
        score = result["risk_score"]
        sender_id = sender.id
        receiver_number = receiver.account_number
        remark = payload.remark
        db.rollback()
        if action == ACTION_STEP_UP:
            raise _store_challenge(db, sender_id, receiver_number, amount, remark, key, result, reasons, score)
        raise _store_held(db, sender_id, receiver.id, amount, remark, key, result, reasons)

    db.commit()
    db.refresh(transaction)
    _publish_completed(transaction, sender, receiver, amount, result)
    return transaction


def _reasons(result: dict | None) -> list[str]:
    if not result:
        return []
    trace = result.get("decision_trace") or {}
    return list(trace.get("context") or []) or [result.get("narrative") or "Risk review"]


def _existing_for_key(db: Session, sender: User, receiver: User, payload: TransferRequest) -> Transaction | None:
    key = payload.idempotency_key
    if not key:
        return None
    found = db.execute(select(Transaction).where(Transaction.idempotency_key == key)).scalar_one_or_none()
    if found is None:
        return None
    same = (
        found.sender_id == sender.id
        and found.receiver_id == receiver.id
        and Decimal(found.amount) == Decimal(payload.amount)
    )
    if not same:
        raise IdempotencyConflict("This confirmation key was already used for a different transfer")
    return found


def _store_challenge(db, sender_id, receiver_number, amount, remark, key, result, reasons, score) -> StepUpRequired:
    code = f"{secrets.randbelow(1_000_000):06d}"
    public_id = str(uuid.uuid4())
    db.add(
        StepUpChallenge(
            public_id=public_id,
            sender_id=sender_id,
            recipient_account_number=receiver_number,
            amount=amount,
            remark=remark,
            idempotency_key=key,
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            risk_score=score,
            evaluation=result,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            used=False,
        )
    )
    db.commit()
    return StepUpRequired(public_id, code, reasons, score)


def _store_held(db, sender_id, receiver_id, amount, remark, key, result, reasons) -> TransactionHeld:
    from app.models.enums import AlertStatus
    from app.models.fraud_alert import FraudAlert
    from app.models.risk_evaluation import RiskEvaluation
    from app.services.case_events import record_case_event

    transaction = Transaction(
        sender_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
        remark=remark,
        status=TransactionStatus.HELD,
        idempotency_key=key,
    )
    db.add(transaction)
    db.flush()
    record = RiskEvaluation(
        transaction_id=transaction.id,
        subject_user_id=result["subject_user_id"],
        subject_role=result["subject_role"],
        risk_score=result["risk_score"],
        tier=result["tier"],
        pattern=result["pattern"],
        signals=result["signals"],
        context_checks=result["context_checks"],
        score_breakdown=result["score_breakdown"],
        rules_version=result["rules_version"],
        narrative=result["narrative"],
        hold_placed=True,
        decision_trace=result.get("decision_trace"),
        outcome="HELD",
    )
    db.add(record)
    alert = FraudAlert(
        transaction_id=transaction.id,
        user_id=result["subject_user_id"],
        status=AlertStatus.OPEN,
        risk_score=result["risk_score"],
        triggered_rules=[
            {
                "rule_name": signal["rule_id"],
                "explanation": signal["explanation"],
                "risk_weight": signal.get("score_contribution", 0),
            }
            for signal in result["signals"]
            if signal.get("score_contribution", 0) > 0
        ],
        subject_user_id=result["subject_user_id"],
        subject_role=result["subject_role"],
        tier=result["tier"],
        pattern=result["pattern"],
        signals=result["signals"],
        context_checks=result["context_checks"],
        score_breakdown=result["score_breakdown"],
        rules_version=result["rules_version"],
        narrative=result["narrative"],
        decision_trace=result.get("decision_trace"),
        outcome="HELD",
    )
    db.add(alert)
    db.flush()
    now = datetime.now(UTC)
    db.add(
        AmountHold(
            user_id=sender_id,
            alert_id=alert.id,
            transaction_id=transaction.id,
            amount=amount,
            status=HoldStatus.ACTIVE,
            kind=HoldKind.RESERVATION.value,
            reason_codes=["held_for_review"],
            expires_at=now + timedelta(days=3650),
            explanation_due_at=now + timedelta(days=7),
            narrative="Held for review. The money has not moved.",
        )
    )
    record_case_event(db, alert.id, "hold_placed", "system", {"transaction_id": transaction.transaction_id})
    db.commit()
    return TransactionHeld(transaction.transaction_id, reasons)


def confirm_step_up(db: Session, sender: User, challenge_id: str, code: str, idempotency_key: str) -> Transaction:
    challenge = db.execute(
        select(StepUpChallenge).where(StepUpChallenge.public_id == challenge_id)
    ).scalar_one_or_none()
    if challenge is None or challenge.sender_id != sender.id:
        raise ChallengeRejected("This confirmation does not match the transfer")
    existing = db.execute(
        select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if challenge.used:
        if existing is not None and existing.sender_id == sender.id:
            return existing
        raise ChallengeRejected("This confirmation was already used")
    if challenge.idempotency_key != idempotency_key:
        raise ChallengeRejected("This confirmation does not match the transfer")
    expires = challenge.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        raise ChallengeRejected("This confirmation has expired")
    digest = hashlib.sha256(code.encode()).hexdigest()
    if digest != challenge.code_hash:
        raise ChallengeRejected("That code does not match")

    receiver = db.execute(
        select(User).where(User.account_number == challenge.recipient_account_number)
    ).scalar_one_or_none()
    if receiver is None:
        raise RecipientNotFoundError("No active account found for the recipient")
    if Decimal(challenge.amount) <= 0:
        raise ChallengeRejected("This confirmation does not match the transfer")

    first_id, second_id = sorted([sender.id, receiver.id])
    wallets = (
        db.execute(
            select(Wallet).where(Wallet.user_id.in_([first_id, second_id])).order_by(Wallet.user_id).with_for_update()
        )
        .scalars()
        .all()
    )
    by_user = {wallet.user_id: wallet for wallet in wallets}
    sender_wallet = by_user[sender.id]
    amount = Decimal(challenge.amount)
    held = active_hold_total(db, sender.id)
    if sender_wallet.balance - held < amount:
        raise InsufficientBalanceError("Insufficient balance for this transfer")

    result = dict(challenge.evaluation)
    result["outcome"] = "STEP_UP_VERIFIED → ALLOW"
    result["narrative"] = (
        f"{result.get('narrative', '')} The transfer was high risk and was allowed after the code was verified."
    ).strip()
    transaction = Transaction(
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=amount,
        remark=challenge.remark,
        status=TransactionStatus.COMPLETED,
        idempotency_key=idempotency_key,
    )
    db.add(transaction)
    db.flush()
    record_transfer(db, sender_wallet, by_user[receiver.id], transaction, amount)
    challenge.used = True
    db.commit()
    db.refresh(transaction)
    _publish_completed(transaction, sender, receiver, amount, result)
    return transaction


def _publish_completed(transaction, sender, receiver, amount, result) -> None:
    event_bus.publish(
        TRANSACTION_COMPLETED,
        TransactionCompletedEvent(
            transaction_id=transaction.transaction_id,
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=amount,
            result=result,
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
