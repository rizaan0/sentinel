"""
Fraud alert endpoints (admin-only): list and inspect alerts, and update
investigation status. The full Admin Dashboard UI lands in Phase 5; this is
the API surface it will consume.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.enums import AlertStatus
from app.models.fraud_alert import FraudAlert
from app.models.user import User
from app.schemas.fraud_alert import FraudAlertResponse

router = APIRouter()


def _to_response(alert: FraudAlert) -> FraudAlertResponse:
    return FraudAlertResponse(
        id=alert.id,
        transaction_id=alert.transaction_id,
        user_id=alert.user_id,
        account_number=alert.user.account_number,
        transaction_public_id=alert.transaction.transaction_id,
        risk_score=alert.risk_score,
        triggered_rules=alert.triggered_rules,
        status=alert.status,
        created_at=alert.created_at,
    )


@router.get("", response_model=list[FraudAlertResponse])
def list_alerts(
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[FraudAlertResponse]:
    query = select(FraudAlert).order_by(FraudAlert.created_at.desc())
    if status_filter is not None:
        query = query.where(FraudAlert.status == status_filter)
    alerts = db.execute(query.limit(limit).offset(offset)).scalars().all()
    return [_to_response(a) for a in alerts]


@router.get("/{alert_id}", response_model=FraudAlertResponse)
def get_alert(
    alert_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return _to_response(alert)


class UpdateAlertStatusRequest(BaseModel):
    status: AlertStatus


@router.patch("/{alert_id}/status", response_model=FraudAlertResponse)
def update_alert_status(
    alert_id: int,
    payload: UpdateAlertStatusRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = payload.status
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _to_response(alert)
