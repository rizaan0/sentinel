"""
Fraud alert endpoints (admin-only): list, inspect, update status, release or
confirm an amount hold, and read per-rule alert statistics.
"""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.amount_hold import AmountHold
from app.models.enums import AlertStatus, HoldStatus
from app.models.fraud_alert import FraudAlert
from app.models.user import User
from app.schemas.fraud_alert import FraudAlertResponse, RuleStat
from app.services.risk.rules import RULES

router = APIRouter()

ALERT_TIERS = {"suspicious", "high", "critical"}


def _rule_label(stored: str) -> str:
    spec = RULES.get(stored)
    return spec.name if spec is not None else stored


def _hold_for(alert: FraudAlert) -> AmountHold | None:
    holds = [hold for hold in getattr(alert, "holds", [])]
    return holds[0] if holds else None


def _to_response(alert: FraudAlert, db: Session) -> FraudAlertResponse:
    hold = db.execute(
        select(AmountHold)
        .where(AmountHold.alert_id == alert.id)
        .order_by(AmountHold.created_at.desc())
    ).scalars().first()
    return FraudAlertResponse(
        id=alert.id,
        transaction_id=alert.transaction_id,
        user_id=alert.user_id,
        account_number=alert.user.account_number,
        transaction_public_id=alert.transaction.transaction_id,
        risk_score=alert.risk_score,
        triggered_rules=[
            {**rule, "rule_name": _rule_label(rule.get("rule_name", ""))}
            for rule in (alert.triggered_rules or [])
        ],
        status=alert.status,
        created_at=alert.created_at,
        subject_role=alert.subject_role,
        tier=alert.tier,
        pattern=alert.pattern,
        signals=[
            {**signal, "rule_name": _rule_label(signal.get("rule_id") or signal.get("rule_name", ""))}
            for signal in (alert.signals or [])
        ],
        context_checks=alert.context_checks or [],
        score_breakdown=alert.score_breakdown,
        narrative=alert.narrative,
        user_explanation=alert.user_explanation,
        hold_amount=str(hold.amount) if hold is not None else None,
        hold_status=hold.status.value if hold is not None else None,
    )


def _release_holds(db: Session, alert: FraudAlert, admin: User, new_status: HoldStatus) -> None:
    holds = db.execute(select(AmountHold).where(AmountHold.alert_id == alert.id)).scalars().all()
    now = datetime.now(UTC)
    for hold in holds:
        if hold.status == HoldStatus.ACTIVE:
            hold.status = new_status
            hold.released_by = admin.id
            hold.released_at = now


@router.get("", response_model=list[FraudAlertResponse])
def list_alerts(
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[FraudAlertResponse]:
    query = (
        select(FraudAlert)
        .where(FraudAlert.tier.in_(ALERT_TIERS))
        .order_by(FraudAlert.created_at.desc())
    )
    if status_filter is not None:
        query = query.where(FraudAlert.status == status_filter)
    alerts = db.execute(query.limit(limit).offset(offset)).scalars().all()
    return [_to_response(alert, db) for alert in alerts]


@router.get("/rule-stats", response_model=list[RuleStat])
def rule_stats(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[RuleStat]:
    alerts = db.execute(select(FraudAlert)).scalars().all()
    counts = {rule_id: {"alerts": 0, "false_positives": 0} for rule_id in RULES}
    for alert in alerts:
        seen = set()
        for signal in alert.signals or []:
            rule_id = signal.get("rule_id")
            if not rule_id or rule_id in seen:
                continue
            seen.add(rule_id)
            bucket = counts.setdefault(rule_id, {"alerts": 0, "false_positives": 0})
            bucket["alerts"] += 1
            if alert.status == AlertStatus.FALSE_POSITIVE:
                bucket["false_positives"] += 1
        if not alert.signals:
            for rule in alert.triggered_rules or []:
                rule_id = rule.get("rule_name")
                bucket = counts.setdefault(rule_id, {"alerts": 0, "false_positives": 0})
                bucket["alerts"] += 1
                if alert.status == AlertStatus.FALSE_POSITIVE:
                    bucket["false_positives"] += 1
    return [RuleStat(rule_id=rule_id, **stats) for rule_id, stats in counts.items()]


@router.get("/{alert_id}", response_model=FraudAlertResponse)
def get_alert(
    alert_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return _to_response(alert, db)


class UpdateAlertStatusRequest(BaseModel):
    status: AlertStatus


@router.patch("/{alert_id}/status", response_model=FraudAlertResponse)
def update_alert_status(
    alert_id: int,
    payload: UpdateAlertStatusRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = payload.status
    if payload.status == AlertStatus.FALSE_POSITIVE:
        _release_holds(db, alert, admin, HoldStatus.RELEASED)
    if payload.status == AlertStatus.CONFIRMED_FRAUD:
        holds = db.execute(select(AmountHold).where(AmountHold.alert_id == alert.id)).scalars().all()
        for hold in holds:
            if hold.status == HoldStatus.ACTIVE:
                hold.status = HoldStatus.CONFIRMED
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _to_response(alert, db)


@router.post("/{alert_id}/release", response_model=FraudAlertResponse)
def release_hold(
    alert_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    _release_holds(db, alert, admin, HoldStatus.RELEASED)
    if alert.status == AlertStatus.OPEN:
        alert.status = AlertStatus.INVESTIGATING
    db.commit()
    db.refresh(alert)
    return _to_response(alert, db)


@router.post("/{alert_id}/confirm", response_model=FraudAlertResponse)
def confirm_fraud(
    alert_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.status = AlertStatus.CONFIRMED_FRAUD
    holds = db.execute(select(AmountHold).where(AmountHold.alert_id == alert.id)).scalars().all()
    for hold in holds:
        if hold.status == HoldStatus.ACTIVE:
            hold.status = HoldStatus.CONFIRMED
            hold.released_by = admin.id
    db.commit()
    db.refresh(alert)
    return _to_response(alert, db)
