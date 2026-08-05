"""
Ledger Service: the source of financial truth (Architecture Rule). Every
wallet balance mutation - genesis funding at signup, or a transfer - goes
through here, and every mutation is paired with a double-entry ledger
record after passing the Integrity Validator.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import LedgerEntryType, LedgerReferenceType
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.services.integrity_validator import validate_double_entry, validate_wallet_delta


def record_genesis_credit(db: Session, wallet: Wallet) -> LedgerEntry:
    """Records the one-time 1000 ST Coins grant a new wallet starts with."""
    entry = LedgerEntry(
        user_id=wallet.user_id,
        transaction_id=None,
        reference_type=LedgerReferenceType.GENESIS,
        entry_type=LedgerEntryType.CREDIT,
        amount=wallet.balance,
        balance_after=wallet.balance,
    )
    db.add(entry)
    return entry


def record_transfer(
    db: Session,
    sender_wallet: Wallet,
    receiver_wallet: Wallet,
    transaction: Transaction,
    amount: Decimal,
) -> tuple[LedgerEntry, LedgerEntry]:
    """
    Applies the balance mutation for a transfer and writes the matching
    double-entry ledger records, validated by the Integrity Validator.
    `transaction` must already be flushed (have an id) before calling this.
    """
    validate_double_entry(amount, amount)

    sender_before = sender_wallet.balance
    receiver_before = receiver_wallet.balance

    sender_wallet.balance = sender_before - amount
    receiver_wallet.balance = receiver_before + amount

    validate_wallet_delta(sender_before, sender_wallet.balance, -amount)
    validate_wallet_delta(receiver_before, receiver_wallet.balance, amount)

    debit_entry = LedgerEntry(
        user_id=sender_wallet.user_id,
        transaction_id=transaction.id,
        reference_type=LedgerReferenceType.TRANSFER,
        entry_type=LedgerEntryType.DEBIT,
        amount=amount,
        balance_after=sender_wallet.balance,
    )
    credit_entry = LedgerEntry(
        user_id=receiver_wallet.user_id,
        transaction_id=transaction.id,
        reference_type=LedgerReferenceType.TRANSFER,
        entry_type=LedgerEntryType.CREDIT,
        amount=amount,
        balance_after=receiver_wallet.balance,
    )
    db.add(debit_entry)
    db.add(credit_entry)
    db.add(sender_wallet)
    db.add(receiver_wallet)
    return debit_entry, credit_entry
