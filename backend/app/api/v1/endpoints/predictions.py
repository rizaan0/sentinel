"""
Predictive Analytics endpoints (admin-only): on-demand run + latest ranked
predictions. A scheduled run also happens automatically
(see app/workers/scheduler.py), mirroring Reconciliation's pattern.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.risk_prediction import RiskPrediction
from app.models.user import User
from app.schemas.prediction import RiskPredictionResponse
from app.services.prediction_service import compute_predictions, get_latest_predictions

router = APIRouter()


def _to_response(prediction: RiskPrediction) -> RiskPredictionResponse:
    return RiskPredictionResponse(
        id=prediction.id,
        user_id=prediction.user_id,
        account_number=prediction.user.account_number,
        predicted_risk_level=prediction.predicted_risk_level,
        trend_score=prediction.trend_score,
        alerts_last_7d=prediction.alerts_last_7d,
        alerts_prior_7d=prediction.alerts_prior_7d,
        avg_risk_score_last_7d=prediction.avg_risk_score_last_7d,
        created_at=prediction.created_at,
    )


@router.post(
    "/run", response_model=list[RiskPredictionResponse], status_code=status.HTTP_201_CREATED
)
def run(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[RiskPredictionResponse]:
    predictions = compute_predictions(db)
    return [_to_response(p) for p in predictions]


@router.get("", response_model=list[RiskPredictionResponse])
def list_latest(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[RiskPredictionResponse]:
    predictions = get_latest_predictions(db)
    return [_to_response(p) for p in predictions]
