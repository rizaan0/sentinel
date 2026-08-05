"""
Risk predictions: the output of Predictive Analytics, estimating which
users/patterns are trending toward increased suspicious activity based on
historical rule/ML signals (per idea.md). This is explanatory forecasting,
not a fraud determination.
"""
from sqlalchemy import Float, ForeignKey
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

    user: Mapped["User"] = relationship()  # noqa: F821
