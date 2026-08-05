"""
Transaction model: the record of a completed transfer between two wallets.

Architecture Rule: PostgreSQL is the single source of truth. `transaction_id`
is the public, receipt-facing identifier (a UUID), independent of the
internal auto-increment primary key.
"""
import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import TransactionStatus


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(280), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(
        default=TransactionStatus.COMPLETED, nullable=False
    )

    sender: Mapped["User"] = relationship(foreign_keys=[sender_id])  # noqa: F821
    receiver: Mapped["User"] = relationship(foreign_keys=[receiver_id])  # noqa: F821
