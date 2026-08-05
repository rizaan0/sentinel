"""
Monitoring Engine: subscribes to the canonical `Transaction Completed Event`
and runs the Rule Engine (and, from Phase 6, the ML Anomaly Detector)
against the transaction. Fraud alerts are created only when at least one
signal triggers - ordinary transactions pass through silently, exactly as
described in idea.md.
"""
import logging

from sqlalchemy import select

from app.core.events import TransactionCompletedEvent
from app.db.session import SessionLocal
from app.models.enums import AlertStatus
from app.models.fraud_alert import FraudAlert
from app.models.transaction import Transaction
from app.services import fraud_rules, ml_anomaly_service
from app.services.fraud_rules import RuleResult
from app.services.realtime import publish_event

logger = logging.getLogger("sentinel.monitoring")

MAX_RISK_SCORE = 100


def evaluate_transaction_event(event: TransactionCompletedEvent) -> None:
    """
    Runs in its own DB session/connection, independent of the payment
    flow's session - Monitoring is a separate consumer of the Transaction
    Completed Event and must never block or depend on the payment path.
    """
    db = SessionLocal()
    try:
        transaction = db.execute(
            select(Transaction).where(Transaction.transaction_id == event.transaction_id)
        ).scalar_one_or_none()
        if transaction is None:
            logger.warning("Monitoring: transaction %s not found", event.transaction_id)
            return

        triggered = [
            result
            for rule in fraud_rules.ALL_RULES
            if (result := rule(db, transaction)) is not None
        ]

        # ML Anomaly Detector: a third parallel evaluator alongside the Rule
        # Engine and Statistics (Architecture). It participates in the same
        # alert-creation gate as the rules, contributing its own weighted
        # "rule-like" result when the model flags the transaction.
        ml_result = ml_anomaly_service.evaluate(db, transaction)
        if ml_result is not None:
            triggered.append(
                RuleResult(
                    rule_name="ml_anomaly_detected",
                    explanation=(
                        "ML Anomaly Detector flagged this transaction as statistically "
                        "unusual for this account (anomaly score "
                        f"{ml_result['anomaly_score']:.3f})."
                    ),
                    risk_weight=35,
                )
            )

        if not triggered:
            return

        risk_score = min(sum(r.risk_weight for r in triggered), MAX_RISK_SCORE)
        alert = FraudAlert(
            transaction_id=transaction.id,
            user_id=transaction.sender_id,
            risk_score=risk_score,
            triggered_rules=[
                {
                    "rule_name": r.rule_name,
                    "explanation": r.explanation,
                    "risk_weight": r.risk_weight,
                }
                for r in triggered
            ],
            status=AlertStatus.OPEN,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info(
            "Fraud alert created: transaction=%s risk_score=%d rules=%s",
            transaction.transaction_id,
            risk_score,
            [r.rule_name for r in triggered],
        )

        publish_event(
            "fraud_alert",
            {
                "alert_id": alert.id,
                "transaction_id": transaction.transaction_id,
                "account_number": transaction.sender.account_number,
                "risk_score": alert.risk_score,
                "triggered_rules": alert.triggered_rules,
                "status": alert.status.value,
                "created_at": alert.created_at,
            },
        )
    finally:
        db.close()
