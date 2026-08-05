"""
Predictive Analytics: estimates which users' behavior is trending toward
increased suspicion, based on the trajectory of their own fraud-alert
history (frequency and severity, last 7 days vs. the 7 days before that).
This is a transparent, explainable heuristic - not a black-box forecast -
consistent with the AI Investigation Assistant's explainability goal.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import RiskLevel
from app.models.fraud_alert import FraudAlert
from app.models.risk_prediction import RiskPrediction

HIGH_THRESHOLD = 60.0
MEDIUM_THRESHOLD = 30.0


def _risk_level_for(trend_score: float) -> RiskLevel:
    if trend_score >= HIGH_THRESHOLD:
        return RiskLevel.HIGH
    if trend_score >= MEDIUM_THRESHOLD:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def compute_predictions(db: Session) -> list[RiskPrediction]:
    now = datetime.now(UTC)
    last_7d_start = now - timedelta(days=7)
    prior_7d_start = now - timedelta(days=14)

    user_ids = db.execute(select(FraudAlert.user_id).distinct()).scalars().all()

    predictions: list[RiskPrediction] = []
    for user_id in user_ids:
        alerts_last_7d = db.execute(
            select(func.count())
            .select_from(FraudAlert)
            .where(FraudAlert.user_id == user_id, FraudAlert.created_at >= last_7d_start)
        ).scalar_one()

        if alerts_last_7d == 0:
            continue  # no current signal worth predicting on

        alerts_prior_7d = db.execute(
            select(func.count())
            .select_from(FraudAlert)
            .where(
                FraudAlert.user_id == user_id,
                FraudAlert.created_at >= prior_7d_start,
                FraudAlert.created_at < last_7d_start,
            )
        ).scalar_one()

        avg_risk_last_7d = db.execute(
            select(func.coalesce(func.avg(FraudAlert.risk_score), 0)).where(
                FraudAlert.user_id == user_id, FraudAlert.created_at >= last_7d_start
            )
        ).scalar_one()

        growth_factor = max(0.0, (alerts_last_7d - alerts_prior_7d) / max(alerts_prior_7d, 1))
        trend_score = min(100.0, float(avg_risk_last_7d) * (1 + growth_factor))

        predictions.append(
            RiskPrediction(
                user_id=user_id,
                predicted_risk_level=_risk_level_for(trend_score),
                trend_score=trend_score,
                alerts_last_7d=alerts_last_7d,
                alerts_prior_7d=alerts_prior_7d,
                avg_risk_score_last_7d=float(avg_risk_last_7d),
            )
        )

    db.add_all(predictions)
    db.commit()
    for prediction in predictions:
        db.refresh(prediction)
    return predictions


def get_latest_predictions(db: Session) -> list[RiskPrediction]:
    """One row per user: their most recently computed prediction, ranked by trend score."""
    latest_per_user = (
        select(RiskPrediction.user_id, func.max(RiskPrediction.created_at).label("latest"))
        .group_by(RiskPrediction.user_id)
        .subquery()
    )
    return (
        db.execute(
            select(RiskPrediction)
            .join(
                latest_per_user,
                (RiskPrediction.user_id == latest_per_user.c.user_id)
                & (RiskPrediction.created_at == latest_per_user.c.latest),
            )
            .order_by(RiskPrediction.trend_score.desc())
        )
        .scalars()
        .all()
    )
