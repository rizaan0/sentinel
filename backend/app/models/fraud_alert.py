"""
Fraud alerts: output of the Monitoring Engine's Rule Engine (and, from
Phase 6, the ML Anomaly Detector). Fraud is never manually marked - it
emerges from behavioral rules evaluated against real transaction activity
(per idea.md).
"""
from sqlalchemy import JSON, ForeignKey
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

    transaction: Mapped["Transaction"] = relationship()  # noqa: F821
    user: Mapped["User"] = relationship()  # noqa: F821
