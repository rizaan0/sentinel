"""
Monitoring Engine: scores a completed transfer and records the decision.
A hold covers only the flagged amount. Soft signals alone never restrict anyone.
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.events import TransactionCompletedEvent
from app.db.session import SessionLocal
from app.models.amount_hold import AmountHold
from app.models.enums import AlertStatus, HoldKind, HoldStatus
from app.services.case_events import record_case_event
from app.models.fraud_alert import FraudAlert
from app.models.risk_evaluation import RiskEvaluation
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.services.realtime import publish_event
from app.services.risk.decision import TIER_HIGH, TIER_SUSPICIOUS, TIER_CRITICAL
from app.services.risk.engine import evaluate

logger = logging.getLogger("sentinel.monitoring")

ALERT_TIERS = {TIER_SUSPICIOUS, TIER_HIGH, TIER_CRITICAL}


def _legacy_rules(signals: list[dict]) -> list[dict]:
    return [
        {
            "rule_name": signal["rule_id"],
            "explanation": signal["explanation"],
            "risk_weight": signal.get("score_contribution", 0),
        }
        for signal in signals
        if signal.get("score_contribution", 0) > 0
    ]


def _place_hold(db, evaluation: dict, alert: FraudAlert, transaction: Transaction) -> AmountHold | None:
    wallet = db.execute(select(Wallet).where(Wallet.user_id == evaluation["subject_user_id"])).scalar_one_or_none()
    balance = float(wallet.balance) if wallet is not None else 0.0
    amount = min(float(evaluation["hold_amount"] or transaction.amount), balance)
    if amount <= 0:
        return None
    now = datetime.now(UTC)
    hold = AmountHold(
        user_id=evaluation["subject_user_id"],
        alert_id=alert.id,
        amount=amount,
        status=HoldStatus.ACTIVE,
        kind=HoldKind.RISK.value,
        reason_codes=[signal["rule_id"] for signal in evaluation["signals"] if signal.get("score_contribution", 0) > 0],
        expires_at=now + timedelta(days=settings.HOLD_MAX_DAYS),
        explanation_due_at=now + timedelta(days=settings.HOLD_EXPLANATION_DAYS),
        narrative=evaluation["narrative"][:2000],
    )
    db.add(hold)
    return hold


def evaluate_transaction_event(event: TransactionCompletedEvent) -> None:
    db = SessionLocal()
    try:
        transaction = db.execute(
            select(Transaction).where(Transaction.transaction_id == event.transaction_id)
        ).scalar_one_or_none()
        if transaction is None:
            logger.warning("Monitoring: transaction %s not found", event.transaction_id)
            return

        result = event.result if event.result is not None else evaluate(db, transaction)
        if result is None:
            return

        record = RiskEvaluation(
            transaction_id=transaction.id,
            subject_user_id=result["subject_user_id"],
            subject_role=result["subject_role"],
            risk_score=result["risk_score"],
            tier=result["tier"],
            pattern=result["pattern"],
            signals=result["signals"],
            context_checks=result["context_checks"],
            score_breakdown=result["score_breakdown"],
            rules_version=result["rules_version"],
            narrative=result["narrative"],
            hold_placed=bool(result["hold"]),
            decision_trace=result.get("decision_trace"),
            outcome=result.get("outcome") or result.get("action"),
        )
        db.add(record)

        if result["tier"] not in ALERT_TIERS:
            db.commit()
            return

        cutoff = datetime.now(UTC) - timedelta(minutes=settings.ALERT_DEDUP_MINUTES)
        existing = db.execute(
            select(FraudAlert)
            .where(
                FraudAlert.user_id == result["subject_user_id"],
                FraudAlert.status.in_([AlertStatus.OPEN, AlertStatus.INVESTIGATING]),
                FraudAlert.created_at >= cutoff,
            )
            .order_by(FraudAlert.created_at.desc())
        ).scalars().first()

        payload = dict(
            risk_score=result["risk_score"],
            triggered_rules=_legacy_rules(result["signals"]),
            subject_user_id=result["subject_user_id"],
            subject_role=result["subject_role"],
            tier=result["tier"],
            pattern=result["pattern"],
            signals=result["signals"],
            context_checks=result["context_checks"],
            score_breakdown=result["score_breakdown"],
            rules_version=result["rules_version"],
            narrative=result["narrative"],
            decision_trace=result.get("decision_trace"),
            outcome=result.get("outcome") or result.get("action"),
        )
        if existing is not None:
            for key, value in payload.items():
                setattr(existing, key, value)
            alert = existing
        else:
            alert = FraudAlert(
                transaction_id=transaction.id,
                user_id=result["subject_user_id"],
                status=AlertStatus.OPEN,
                **payload,
            )
            db.add(alert)
        db.flush()
        record_case_event(
            db,
            alert.id,
            "alert_updated" if existing is not None else "alert_created",
            "system",
            {"tier": result["tier"], "risk_score": result["risk_score"]},
        )

        if result["hold"]:
            _place_hold(db, result, alert, transaction)

        db.commit()
        db.refresh(alert)
        publish_event(
            "fraud_alert",
            {
                "alert_id": alert.id,
                "transaction_id": transaction.transaction_id,
                "account_number": alert.user.account_number if alert.user else None,
                "risk_score": alert.risk_score,
                "triggered_rules": alert.triggered_rules,
                "tier": alert.tier,
                "pattern": alert.pattern,
                "status": alert.status.value,
                "created_at": alert.created_at,
            },
        )
    finally:
        db.close()
