"""
Integrity Validator: re-checks transaction arithmetic as part of the
ledger-write path (Architecture: this runs inside the Ledger Service, before
any ledger entry is persisted).
"""
from decimal import Decimal


class LedgerIntegrityError(Exception):
    pass


def validate_double_entry(debit_amount: Decimal, credit_amount: Decimal) -> None:
    """A double-entry pair must move the exact same amount on both sides."""
    if debit_amount != credit_amount:
        raise LedgerIntegrityError(
            f"Ledger integrity violation: debit {debit_amount} != credit {credit_amount}"
        )
    if debit_amount <= 0:
        raise LedgerIntegrityError(
            f"Ledger integrity violation: non-positive amount {debit_amount}"
        )


def validate_wallet_delta(previous_balance: Decimal, new_balance: Decimal, delta: Decimal) -> None:
    """The wallet's new balance must exactly equal previous +/- delta."""
    if previous_balance + delta != new_balance:
        raise LedgerIntegrityError(
            f"Ledger integrity violation: {previous_balance} + ({delta}) != {new_balance}"
        )
