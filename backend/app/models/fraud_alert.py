"""
Fraud alerts: output of the Monitoring Engine's Rule Engine (and, from
Phase 6, the ML Anomaly Detector). Fraud is never manually marked - it
emerges from behavioral rules evaluated against real transaction activity
(per idea.md).
"""
from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import AlertStatus


class FraudAlert(Base, TimestampMixin):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )  # the account whose behavior triggered the alert (the sender)
    risk_score: Mapped[int] = mapped_column(nullable=False)  # 0-100, rule-based component
    triggered_rules: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[AlertStatus] = mapped_column(default=AlertStatus.OPEN, nullable=False)
    subject_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    subject_role: Mapped[str | None] = mapped_column(nullable=True)
    tier: Mapped[str | None] = mapped_column(nullable=True)
    pattern: Mapped[str | None] = mapped_column(nullable=True)
    signals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    context_checks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rules_version: Mapped[str | None] = mapped_column(nullable=True)
    user_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    transaction: Mapped["Transaction"] = relationship()  # noqa: F821
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
