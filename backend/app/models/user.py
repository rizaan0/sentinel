"""
User model.

Architecture Rule: PostgreSQL is the single source of truth. The user's
account_number is their public identifier for sending/receiving money,
completely independent of any real banking identifier (per idea.md).
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)

    wallet: Mapped["Wallet"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    pin_credential: Mapped["PinCredential"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def pin_is_set(self) -> bool:
        return self.pin_credential is not None

    @property
    def balance(self):
        return self.wallet.balance if self.wallet is not None else None
