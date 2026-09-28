"""
Retrieval Service (RAG): reads directly from PostgreSQL to assemble the
context the AI Investigation Assistant needs to answer a question about a
transaction or a user's recent behavior. Reconciliation Reports are pulled
in as a second, parallel context source (Architecture: they converge
before the LLM call), so the assistant can explain reconciliation
discrepancies as well as fraud alerts.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.amount_hold import AmountHold
from app.models.case_event import CaseEvent
from app.models.fraud_alert import FraudAlert
from app.models.reconciliation_report import ReconciliationReport
from app.models.risk_prediction import RiskPrediction
from app.models.transaction import Transaction
from app.models.user import User

HISTORY_WINDOW_DAYS = 7
HISTORY_LIMIT = 20
RECENT_REPORTS_LIMIT = 3


def _serialize_transaction(tx: Transaction) -> dict:
    return {
        "transaction_id": tx.transaction_id,
        "sender_account_number": tx.sender.account_number,
        "sender_name": tx.sender.full_name,
        "receiver_account_number": tx.receiver.account_number,
        "receiver_name": tx.receiver.full_name,
        "amount": str(tx.amount),
        "remark": tx.remark,
        "status": tx.status.value,
        "created_at": tx.created_at.isoformat(),
    }


def _serialize_alert(db: Session, alert: FraudAlert) -> dict:
    hold = db.execute(
        select(AmountHold)
        .where(AmountHold.alert_id == alert.id)
        .order_by(AmountHold.created_at.desc())
    ).scalars().first()
    return {
        "risk_score": alert.risk_score,
        "status": alert.status.value,
        "triggered_rules": alert.triggered_rules,
        "created_at": alert.created_at.isoformat(),
        "transaction_id": alert.transaction.transaction_id,
        "tier": alert.tier,
        "pattern": alert.pattern,
        "subject_role": alert.subject_role,
        "signals": alert.signals or [],
        "context_checks": alert.context_checks or [],
        "score_breakdown": alert.score_breakdown,
        "narrative": alert.narrative,
        "user_explanation": alert.user_explanation,
        "decision_trace": alert.decision_trace,
        "outcome": alert.outcome,
        "reviews": [
            {"actor": event.actor, "detail": event.detail, "created_at": event.created_at.isoformat()}
            for event in db.execute(
                select(CaseEvent).where(CaseEvent.alert_id == alert.id, CaseEvent.kind == "review")
            ).scalars().all()
        ],
        "hold": None
        if hold is None
        else {"amount": str(hold.amount), "status": hold.status.value},
    }


def build_context_for_transaction(db: Session, transaction: Transaction) -> dict:
    """Everything relevant to explain why a specific transaction was flagged."""
    sender = transaction.sender

    alerts = (
        db.execute(select(FraudAlert).where(FraudAlert.transaction_id == transaction.id))
        .scalars()
        .all()
    )

    since = transaction.created_at - timedelta(days=HISTORY_WINDOW_DAYS)
    recent_history = (
        db.execute(
            select(Transaction)
            .where(
                Transaction.sender_id == sender.id,
                Transaction.created_at >= since,
                Transaction.created_at <= transaction.created_at,
            )
            .order_by(Transaction.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
        .scalars()
        .all()
    )

    return {
        "transaction": _serialize_transaction(transaction),
        "fraud_alerts": [_serialize_alert(db, a) for a in alerts],
        "sender_recent_history": [_serialize_transaction(t) for t in recent_history],
        "reconciliation_reports": _recent_reconciliation_reports(db),
    }


def build_context_for_account(db: Session, account_number: str) -> dict:
    """Summarizes a user's recent behavior, for questions not tied to one transaction."""
    user = db.execute(
        select(User).where(User.account_number == account_number)
    ).scalar_one_or_none()
    if user is None:
        return {"error": f"No account found with number {account_number}"}

    since = datetime.now(UTC) - timedelta(days=HISTORY_WINDOW_DAYS)
    recent_history = (
        db.execute(
            select(Transaction)
            .where(Transaction.sender_id == user.id, Transaction.created_at >= since)
            .order_by(Transaction.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
        .scalars()
        .all()
    )

    alerts = (
        db.execute(
            select(FraudAlert)
            .where(FraudAlert.user_id == user.id, FraudAlert.created_at >= since)
            .order_by(FraudAlert.created_at.desc())
        )
        .scalars()
        .all()
    )

    forecast = db.execute(
        select(RiskPrediction)
        .where(RiskPrediction.user_id == user.id)
        .order_by(RiskPrediction.created_at.desc())
    ).scalars().first()

    return {
        "account_number": user.account_number,
        "full_name": user.full_name,
        "recent_history": [_serialize_transaction(t) for t in recent_history],
        "recent_fraud_alerts": [_serialize_alert(db, a) for a in alerts],
        "reconciliation_reports": _recent_reconciliation_reports(db),
        "risk_forecast": None
        if forecast is None
        else {
            "current_risk": forecast.current_risk,
            "predicted_7d_risk": forecast.predicted_7d_risk,
            "risk_change": forecast.risk_change,
            "trend": forecast.trend,
            "horizon_days": forecast.horizon_days,
            "drivers": forecast.drivers or [],
            "explanation": forecast.explanation,
            "series": forecast.series or [],
        },
    }


def _recent_reconciliation_reports(db: Session) -> list[dict]:
    reports = (
        db.execute(
            select(ReconciliationReport)
            .order_by(ReconciliationReport.created_at.desc())
            .limit(RECENT_REPORTS_LIMIT)
        )
        .scalars()
        .all()
    )
    return [
        {
            "status": r.status.value,
            "accounts_checked": r.accounts_checked,
            "discrepancy_count": r.discrepancy_count,
            "discrepancies": r.discrepancies,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]
