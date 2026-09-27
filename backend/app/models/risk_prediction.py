"""
Risk predictions: the output of Predictive Analytics, estimating which
users/patterns are trending toward increased suspicious activity based on
historical rule/ML signals (per idea.md). This is explanatory forecasting,
not a fraud determination.
"""
from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import RiskLevel


class RiskPrediction(Base, TimestampMixin):
    __tablename__ = "risk_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    predicted_risk_level: Mapped[RiskLevel] = mapped_column(nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False)
    alerts_last_7d: Mapped[int] = mapped_column(nullable=False)
    alerts_prior_7d: Mapped[int] = mapped_column(nullable=False)
    avg_risk_score_last_7d: Mapped[float] = mapped_column(Float, nullable=False)
    current_risk: Mapped[int] = mapped_column(default=0, nullable=False)
    predicted_7d_risk: Mapped[int] = mapped_column(default=0, nullable=False)
    risk_change: Mapped[int] = mapped_column(default=0, nullable=False)
    trend: Mapped[str] = mapped_column(String(16), default="stable", nullable=False)
    horizon_days: Mapped[int] = mapped_column(default=7, nullable=False)
    series: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    drivers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)

    user: Mapped["User"] = relationship()  # noqa: F821
