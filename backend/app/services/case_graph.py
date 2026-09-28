"""One case: the people, transfers, rules, and the order they happened."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account_restriction import AccountRestriction
from app.models.amount_hold import AmountHold
from app.models.case_event import CaseEvent
from app.models.fraud_alert import FraudAlert
from app.models.reconciliation_report import ReconciliationReport
from app.models.risk_evaluation import RiskEvaluation
from app.models.transaction import Transaction
from app.models.user import User


def build_case(db: Session, alert: FraudAlert) -> dict:
    flagged = alert.transaction
    start = flagged.created_at - timedelta(minutes=settings.R10_WINDOW_MINUTES)
    end = flagged.created_at + timedelta(minutes=settings.R10_WINDOW_MINUTES)
    account_ids = {alert.user_id, alert.subject_user_id or alert.user_id, flagged.sender_id, flagged.receiver_id}
    for signal in alert.signals or []:
        for sender_id in (signal.get("evidence") or {}).get("sender_ids") or []:
            account_ids.add(sender_id)
    transfers = db.execute(
        select(Transaction).where(
            Transaction.created_at >= start,
            Transaction.created_at <= end,
            (Transaction.sender_id.in_(account_ids)) | (Transaction.receiver_id.in_(account_ids)),
        )
    ).scalars().all()
    for transfer in transfers:
        account_ids.add(transfer.sender_id)
        account_ids.add(transfer.receiver_id)
    users = db.execute(select(User).where(User.id.in_(account_ids))).scalars().all()
    by_id = {user.id: user for user in users}
    holds = db.execute(select(AmountHold).where(AmountHold.alert_id == alert.id)).scalars().all()
    restrictions = db.execute(
        select(AccountRestriction).where(AccountRestriction.alert_id == alert.id)
    ).scalars().all()
    evaluations = db.execute(
        select(RiskEvaluation).where(RiskEvaluation.transaction_id.in_([item.id for item in transfers] or [-1]))
    ).scalars().all()
    events = db.execute(
        select(CaseEvent).where(CaseEvent.alert_id == alert.id).order_by(CaseEvent.created_at)
    ).scalars().all()

    nodes = []
    edges = []
    subject_id = alert.subject_user_id or alert.user_id
    for user in users:
        nodes.append(
            {
                "id": f"account:{user.id}",
                "type": "account",
                "label": user.full_name,
                "account_number": user.account_number,
                "role": "subject" if user.id == subject_id else "counterparty",
            }
        )
    for transfer in transfers:
        node_id = f"transaction:{transfer.id}"
        nodes.append(
            {
                "id": node_id,
                "type": "transaction",
                "label": str(transfer.amount),
                "status": transfer.status.value,
                "created_at": transfer.created_at.isoformat(),
            }
        )
        edges.append({"from": f"account:{transfer.sender_id}", "to": node_id, "type": "sent"})
        edges.append({"from": node_id, "to": f"account:{transfer.receiver_id}", "type": "received"})
    for signal in alert.signals or []:
        rule_id = f"rule:{signal['rule_id']}"
        nodes.append(
            {
                "id": rule_id,
                "type": "ml" if signal["rule_id"] == "ML" else "rule",
                "label": signal.get("rule_name") or signal["rule_id"],
                "points": signal.get("score_contribution", 0),
            }
        )
        edges.append({"from": rule_id, "to": f"transaction:{flagged.id}", "type": "fired"})
    for hold in holds:
        node_id = f"hold:{hold.id}"
        nodes.append(
            {
                "id": node_id,
                "type": "quarantine" if hold.kind == "quarantine" else "hold",
                "label": str(hold.amount),
                "status": hold.status.value,
                "kind": hold.kind,
            }
        )
        edges.append({"from": node_id, "to": f"account:{hold.user_id}", "type": "hold"})
    for restriction in restrictions:
        nodes.append(
            {
                "id": f"restriction:{restriction.id}",
                "type": "restriction",
                "label": restriction.scope,
                "active": restriction.active,
                "user_id": restriction.user_id,
            }
        )
    report = db.execute(
        select(ReconciliationReport).order_by(ReconciliationReport.created_at.desc())
    ).scalars().first()
    if report is not None:
        nodes.append(
            {
                "id": f"reconciliation:{report.id}",
                "type": "reconciliation",
                "label": report.status.value,
                "created_at": report.created_at.isoformat(),
            }
        )
    if alert.user_explanation:
        nodes.append({"id": f"explanation:{alert.id}", "type": "explanation", "label": alert.user_explanation})

    timeline = []
    for transfer in transfers:
        sender = by_id.get(transfer.sender_id)
        receiver = by_id.get(transfer.receiver_id)
        timeline.append(
            {
                "at": transfer.created_at.isoformat(),
                "kind": "transfer",
                "text": (
                    f"{sender.full_name if sender else 'Account'} sent {transfer.amount} ST to "
                    f"{receiver.full_name if receiver else 'account'}"
                ),
            }
        )
    for evaluation in evaluations:
        timeline.append(
            {
                "at": evaluation.created_at.isoformat(),
                "kind": "evaluation",
                "text": f"Score {evaluation.risk_score}, tier {evaluation.tier}",
                "score": evaluation.risk_score,
            }
        )
    for event in events:
        timeline.append(
            {
                "at": event.created_at.isoformat(),
                "kind": event.kind,
                "text": event.kind.replace("_", " "),
                "actor": event.actor,
                "detail": event.detail,
            }
        )
    timeline.sort(key=lambda item: item["at"])
    return {
        "title": f"Case #{alert.id}",
        "nodes": nodes,
        "edges": edges,
        "timeline": timeline,
        "decision_trace": alert.decision_trace,
        "outcome": alert.outcome,
        "narrative": alert.narrative,
    }
