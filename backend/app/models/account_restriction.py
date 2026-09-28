"""Outgoing-only restriction on a confirmed subject. Incoming transfers still work."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class AccountRestriction(Base, TimestampMixin):
    __tablename__ = "account_restrictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("fraud_alerts.id"), nullable=True)
    scope: Mapped[str] = mapped_column(String(32), default="outgoing", nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False)
