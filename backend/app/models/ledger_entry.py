"""
Ledger entries: the double-entry accounting record that is the source of
financial truth (Architecture Rule). Every wallet balance change - the
initial 1000 ST Coins grant at signup, or a transfer - is recorded here.
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import LedgerEntryType, LedgerReferenceType


class LedgerEntry(Base, TimestampMixin):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True, index=True
    )
    reference_type: Mapped[LedgerReferenceType] = mapped_column(nullable=False)
    entry_type: Mapped[LedgerEntryType] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    user: Mapped["User"] = relationship()  # noqa: F821
    transaction: Mapped["Transaction | None"] = relationship()  # noqa: F821
