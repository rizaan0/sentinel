"""
Wallet model: current-balance snapshot for a user.

Note: once Phase 3 introduces the Ledger Service, ledger_entries become the
source of financial truth and this balance is kept in sync by that service
(Architecture Rule: the Ledger Service is the source of financial truth).
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base_class import Base, TimestampMixin


class Wallet(Base, TimestampMixin):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=settings.INITIAL_BALANCE, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), default="ST", server_default="ST")

    user: Mapped["User"] = relationship(back_populates="wallet")  # noqa: F821
