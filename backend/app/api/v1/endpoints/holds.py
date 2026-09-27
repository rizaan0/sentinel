"""Account-holder view of amount holds and their explanation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amount_hold import AmountHold
from app.models.enums import HoldStatus
from app.models.fraud_alert import FraudAlert
from app.models.user import User
from app.schemas.fraud_alert import ExplanationRequest, HoldResponse
from app.services.transfer_service import active_hold_total

router = APIRouter()


def _to_hold(hold: AmountHold, db: Session) -> HoldResponse:
    explanation = None
    if hold.alert_id is not None:
        alert = db.get(FraudAlert, hold.alert_id)
        explanation = alert.user_explanation if alert is not None else None
    return HoldResponse(
        id=hold.id,
        amount=str(hold.amount),
        status=hold.status,
        reason_codes=hold.reason_codes or [],
        expires_at=hold.expires_at,
        explanation_due_at=hold.explanation_due_at,
        narrative=hold.narrative,
        user_explanation=explanation,
    )


@router.get("/me", response_model=list[HoldResponse])
def my_holds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HoldResponse]:
    active_hold_total(db, current_user.id)
    holds = (
        db.execute(
            select(AmountHold)
            .where(AmountHold.user_id == current_user.id, AmountHold.status == HoldStatus.ACTIVE)
            .order_by(AmountHold.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [_to_hold(hold, db) for hold in holds]


@router.post("/{hold_id}/explanation", response_model=HoldResponse)
def explain_hold(
    hold_id: int,
    payload: ExplanationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HoldResponse:
    hold = db.get(AmountHold, hold_id)
    if hold is None or hold.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    if hold.alert_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    alert = db.get(FraudAlert, hold.alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    alert.user_explanation = payload.text
    db.commit()
    db.refresh(hold)
    return _to_hold(hold, db)
