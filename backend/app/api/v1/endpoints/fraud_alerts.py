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
from app.models.account_restriction import AccountRestriction
from app.models.enums import HoldKind, TransactionStatus
from app.models.risk_evaluation import RiskEvaluation
from app.schemas.fraud_alert import FraudAlertResponse, PatternFeedback, RuleStat
from app.services.case_events import record_case_event
from app.services.case_graph import build_case
from app.services.containment_service import reject_held, settle_held, trace_and_quarantine
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
        decision_trace=alert.decision_trace,
        outcome=alert.outcome,
    )


def _confirm(db: Session, alert: FraudAlert, admin: User) -> None:
    if alert.transaction is not None and alert.transaction.status == TransactionStatus.HELD:
        reject_held(db, alert, admin.full_name)
        return
    holds = db.execute(select(AmountHold).where(AmountHold.alert_id == alert.id)).scalars().all()
    for hold in holds:
        if hold.status == HoldStatus.ACTIVE and hold.kind == HoldKind.RISK.value:
            hold.status = HoldStatus.CONFIRMED
            hold.released_by = admin.id
    trace_and_quarantine(db, alert, admin.full_name)
    record_case_event(db, alert.id, "status_change", admin.full_name, {"status": "confirmed_fraud"})


@router.post("/{alert_id}/restriction/lift", response_model=FraudAlertResponse)
def lift_restriction(
    alert_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    rows = db.execute(
        select(AccountRestriction).where(AccountRestriction.alert_id == alert.id, AccountRestriction.active.is_(True))
    ).scalars().all()
    for row in rows:
        row.active = False
    record_case_event(db, alert.id, "restriction", admin.full_name, {"active": False})
    db.commit()
    db.refresh(alert)
    return _to_response(alert, db)


@router.post("/{alert_id}/quarantine/{hold_id}/release", response_model=FraudAlertResponse)
def release_quarantine(
    alert_id: int,
    hold_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FraudAlertResponse:
    alert = db.get(FraudAlert, alert_id)
    hold = db.get(AmountHold, hold_id)
    if alert is None or hold is None or hold.alert_id != alert.id or hold.kind != HoldKind.QUARANTINE.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarantine not found")
    hold.status = HoldStatus.RELEASED
    hold.released_by = admin.id
    hold.released_at = datetime.now(UTC)
    record_case_event(db, alert.id, "quarantine", admin.full_name, {"hold_id": hold.id, "released": True})
    db.commit()
    db.refresh(alert)
    return _to_response(alert, db)


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


@router.get("/pattern-feedback", response_model=PatternFeedback)
def pattern_feedback(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PatternFeedback:
    rows = db.execute(select(RiskEvaluation)).scalars().all()
    matched = stayed = confirmed = 0
    for row in rows:
        checks = row.context_checks or []
        if not any(check.get("check") == "reviewed_legitimate_pattern" and check.get("cleared") for check in checks):
            continue
        matched += 1
        if row.tier not in ALERT_TIERS:
            stayed += 1
        later = db.execute(
            select(FraudAlert.id).where(
                FraudAlert.user_id == row.subject_user_id,
                FraudAlert.status == AlertStatus.CONFIRMED_FRAUD,
                FraudAlert.created_at >= row.created_at,
            )
        ).scalars().first()
        if later is not None:
            confirmed += 1
    return PatternFeedback(matched=matched, stayed_under_alert=stayed, later_confirmed=confirmed)


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
    reason: str | None = None
    note: str | None = None


@router.get("/{alert_id}/case")
def get_case(
    alert_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return build_case(db, alert)


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
    if payload.status == AlertStatus.FALSE_POSITIVE and not payload.reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A false positive needs a reason")
    alert.status = payload.status
    if payload.status == AlertStatus.FALSE_POSITIVE:
        _release_holds(db, alert, admin, HoldStatus.RELEASED)
        signature = (alert.decision_trace or {}).get("signature") or {}
        record_case_event(
            db,
            alert.id,
            "review",
            admin.full_name,
            {
                "reason": payload.reason,
                "note": payload.note,
                "subject_user_id": alert.subject_user_id or alert.user_id,
                **signature,
            },
        )
    if payload.status == AlertStatus.CONFIRMED_FRAUD:
        _confirm(db, alert, admin)
    record_case_event(db, alert.id, "status_change", admin.full_name, {"status": payload.status.value})
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
    if alert.transaction is not None and alert.transaction.status == TransactionStatus.HELD:
        settle_held(db, alert, admin.full_name)
    else:
        _release_holds(db, alert, admin, HoldStatus.RELEASED)
    if alert.status == AlertStatus.OPEN:
        alert.status = AlertStatus.INVESTIGATING
    record_case_event(db, alert.id, "hold_released", admin.full_name, {})
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
    _confirm(db, alert, admin)
    db.commit()
    db.refresh(alert)
    return _to_response(alert, db)
