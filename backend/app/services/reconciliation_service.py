"""
Reconciliation Engine: validates the ledger directly (Architecture: it
operates on the Ledger Service's output, independent of the Monitoring/
fraud pipeline). For every wallet, the sum of its ledger entries must equal
its current balance; any mismatch is a discrepancy worth investigating.
"""
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.enums import LedgerEntryType, ReconciliationStatus
from app.models.ledger_entry import LedgerEntry
from app.models.reconciliation_report import ReconciliationReport
from app.models.user import User
from app.models.wallet import Wallet


def run_reconciliation(db: Session, triggered_by: str = "manual") -> ReconciliationReport:
    ledger_sums: dict[int, Decimal] = dict(
        db.execute(
            select(
                LedgerEntry.user_id,
                func.sum(
                    case(
                        (LedgerEntry.entry_type == LedgerEntryType.CREDIT, LedgerEntry.amount),
                        else_=-LedgerEntry.amount,
                    )
                ),
            ).group_by(LedgerEntry.user_id)
        ).all()
    )

    wallets = db.execute(
        select(Wallet, User.account_number).join(User, User.id == Wallet.user_id)
    ).all()

    discrepancies = []
    for wallet, account_number in wallets:
        expected = ledger_sums.get(wallet.user_id, Decimal("0.00"))
        actual = wallet.balance
        if expected != actual:
            discrepancies.append(
                {
                    "user_id": wallet.user_id,
                    "account_number": account_number,
                    "expected_balance": str(expected),
                    "actual_balance": str(actual),
                    "difference": str(actual - expected),
                }
            )

    report = ReconciliationReport(
        status=(
            ReconciliationStatus.DISCREPANCIES_FOUND
            if discrepancies
            else ReconciliationStatus.CLEAN
        ),
        accounts_checked=len(wallets),
        discrepancy_count=len(discrepancies),
        discrepancies=discrepancies,
        triggered_by=triggered_by,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
