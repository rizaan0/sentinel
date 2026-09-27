"""Every evaluation where at least one rule fired, including allows."""

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class RiskEvaluation(Base, TimestampMixin):
    __tablename__ = "risk_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    subject_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    subject_role: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_score: Mapped[int] = mapped_column(nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    pattern: Mapped[str | None] = mapped_column(String(8), nullable=True)
    signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    context_checks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rules_version: Mapped[str] = mapped_column(String(16), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    hold_placed: Mapped[bool] = mapped_column(default=False, nullable=False)
