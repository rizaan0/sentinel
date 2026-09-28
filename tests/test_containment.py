"""Step-up, held transfers, quarantine, counterfactuals, and case timeline."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models.account_restriction import AccountRestriction
from app.models.amount_hold import AmountHold
from app.models.case_event import CaseEvent
from app.models.enums import AlertStatus, HoldKind, HoldStatus, TransactionStatus
from app.models.fraud_alert import FraudAlert
from app.models.ledger_entry import LedgerEntry
from app.models.risk_evaluation import RiskEvaluation
from app.models.step_up_challenge import StepUpChallenge
from app.models.transaction import Transaction
from app.models.user import User
from app.services.case_graph import build_case
from app.services.containment_service import trace_and_quarantine
from app.services.risk.decision import ACTION_ALLOW, score
from app.services.risk.engine import _decision_trace, _rescore
from app.services.transfer_service import active_hold_total
from fraud_helpers import signup_with_pin


def _high_result(sender_id: int):
    signal = {
        "rule_id": "R08",
        "rule_name": "Rapid inbound to outbound",
        "family": "flow",
        "severity": "strong",
        "score_contribution": 35,
        "base_weight": 35,
        "modifier": 0,
        "explanation": "Most of the money moved on.",
        "evidence": {"forward_ratio": 0.9, "window_minutes": 30},
        "triggered": True,
    }
    other = {
        "rule_id": "R05",
        "rule_name": "Unusually large transfer",
        "family": "amount",
        "severity": "medium",
        "score_contribution": 25,
        "base_weight": 25,
        "modifier": 0,
        "explanation": "Large for this account.",
        "evidence": {},
        "triggered": True,
    }
    raw = [signal, other]
    trace = _decision_trace(raw, raw, [], 73, "step_up")
    return {
        "subject_user_id": sender_id,
        "subject_role": "sender",
        "tier": "high",
        "pattern": "E",
        "signals": raw,
        "context_checks": [],
        "score_breakdown": {"final": 73, "strong": 35, "other": 25},
        "risk_score": 73,
        "rules_version": "1",
        "narrative": "High risk.",
        "hold": True,
        "hold_amount": 10,
        "action": "step_up",
        "decision_trace": trace,
        "signature": {"subject_user_id": sender_id, "sender_ids": [], "onward_recipient_id": None, "families": ["flow"]},
    }


def test_step_up_rejects_bad_codes_and_keeps_the_score(client, db_session, monkeypatch):
    sender, headers = signup_with_pin(client, "otp_sender@example.com", pin="1111")
    receiver, _ = signup_with_pin(client, "otp_receiver@example.com")

    def fake_eval(db, transaction):
        result = _high_result(transaction.sender_id)
        result["action"] = "step_up"
        return result

    monkeypatch.setattr("app.services.transfer_service.evaluate", fake_eval)
    key = "otp-key-1"
    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": receiver["account_number"],
            "amount": "15.00",
            "pin": "1111",
            "idempotency_key": key,
        },
        headers=headers,
    )
    assert response.status_code == 428
    body = response.json()
    db_session.expire_all()
    assert db_session.execute(select(Transaction)).scalars().first() is None
    assert db_session.execute(select(LedgerEntry).where(LedgerEntry.reference_type == "transfer")).scalars().first() is None
    challenge = db_session.execute(select(StepUpChallenge)).scalar_one()
    assert challenge.used is False

    challenge.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    expired = client.post(
        "/api/v1/transactions/transfer/confirm",
        json={"challenge_id": body["challenge_id"], "code": body["code"], "idempotency_key": key},
        headers=headers,
    )
    assert expired.status_code == 400

    challenge.expires_at = datetime.now(UTC) + timedelta(minutes=5)
    db_session.commit()
    mismatch = client.post(
        "/api/v1/transactions/transfer/confirm",
        json={"challenge_id": body["challenge_id"], "code": "000000", "idempotency_key": key},
        headers=headers,
    )
    assert mismatch.status_code == 400
    wrong_key = client.post(
        "/api/v1/transactions/transfer/confirm",
        json={"challenge_id": body["challenge_id"], "code": body["code"], "idempotency_key": "other-key"},
        headers=headers,
    )
    assert wrong_key.status_code == 400

    challenge.expires_at = datetime.now(UTC) + timedelta(minutes=5)
    db_session.commit()
    ok = client.post(
        "/api/v1/transactions/transfer/confirm",
        json={"challenge_id": body["challenge_id"], "code": body["code"], "idempotency_key": key},
        headers=headers,
    )
    assert ok.status_code == 201
    again = client.post(
        "/api/v1/transactions/transfer/confirm",
        json={"challenge_id": body["challenge_id"], "code": body["code"], "idempotency_key": key},
        headers=headers,
    )
    assert again.status_code == 201
    assert again.json()["transaction_id"] == ok.json()["transaction_id"]
    db_session.expire_all()
    evaluation = db_session.execute(select(RiskEvaluation)).scalar_one()
    assert evaluation.risk_score == 73
    assert evaluation.outcome == "STEP_UP_VERIFIED → ALLOW"
    assert db_session.execute(select(Transaction)).scalars().all().__len__() == 1


def test_held_transfer_settles_and_rejects(client, db_session, admin_headers, monkeypatch):
    sender, headers = signup_with_pin(client, "held_sender@example.com", pin="1111")
    receiver, _ = signup_with_pin(client, "held_receiver@example.com")

    def fake_eval(db, transaction):
        result = _high_result(transaction.sender_id)
        result["tier"] = "critical"
        result["action"] = "hold_transaction"
        result["risk_score"] = 90
        return result

    monkeypatch.setattr("app.services.transfer_service.evaluate", fake_eval)
    held = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": receiver["account_number"],
            "amount": "20.00",
            "pin": "1111",
            "idempotency_key": "held-1",
        },
        headers=headers,
    )
    assert held.status_code == 202
    db_session.expire_all()
    transaction = db_session.execute(select(Transaction)).scalar_one()
    assert transaction.status == TransactionStatus.HELD
    assert db_session.execute(select(LedgerEntry).where(LedgerEntry.transaction_id == transaction.id)).scalars().first() is None
    reservation = db_session.execute(select(AmountHold)).scalar_one()
    assert reservation.kind == HoldKind.RESERVATION.value

    alert = db_session.execute(select(FraudAlert)).scalar_one()
    released = client.post(f"/api/v1/fraud-alerts/{alert.id}/release", headers=admin_headers)
    assert released.status_code == 200
    db_session.expire_all()
    assert db_session.get(Transaction, transaction.id).status == TransactionStatus.COMPLETED

    sender2, headers2 = signup_with_pin(client, "held2@example.com", pin="1111")
    receiver2, _ = signup_with_pin(client, "held2r@example.com")
    held_again = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": receiver2["account_number"],
            "amount": "20.00",
            "pin": "1111",
            "idempotency_key": "held-2",
        },
        headers=headers2,
    )
    assert held_again.status_code == 202
    alert2 = db_session.execute(
        select(FraudAlert).where(FraudAlert.user_id == sender2["id"])
    ).scalar_one()
    confirmed = client.post(f"/api/v1/fraud-alerts/{alert2.id}/confirm", headers=admin_headers)
    assert confirmed.status_code == 200
    db_session.expire_all()
    rejected = db_session.execute(
        select(Transaction).where(Transaction.sender_id == sender2["id"])
    ).scalar_one()
    assert rejected.status == TransactionStatus.REJECTED


def test_chain_quarantine_restricts_only_the_subject(client, db_session, admin_headers):
    subject, _ = signup_with_pin(client, "chain_subject@example.com", pin="1111")
    hop, hop_headers = signup_with_pin(client, "chain_hop@example.com", pin="1111")
    end, _ = signup_with_pin(client, "chain_end@example.com")
    outsider, outsider_headers = signup_with_pin(client, "chain_out@example.com", pin="1111")
    now = datetime.now(UTC)
    first = Transaction(
        sender_id=subject["id"],
        receiver_id=hop["id"],
        amount=Decimal("40.00"),
        status=TransactionStatus.COMPLETED,
        created_at=now,
    )
    second = Transaction(
        sender_id=hop["id"],
        receiver_id=end["id"],
        amount=Decimal("30.00"),
        status=TransactionStatus.COMPLETED,
        created_at=now,
    )
    db_session.add_all([first, second])
    db_session.flush()
    alert = FraudAlert(
        transaction_id=first.id,
        user_id=subject["id"],
        subject_user_id=subject["id"],
        risk_score=90,
        triggered_rules=[],
        status=AlertStatus.CONFIRMED_FRAUD,
        tier="critical",
        signals=[{"rule_id": "R10", "score_contribution": 45, "hold_basis": 40, "evidence": {}}],
    )
    db_session.add(alert)
    db_session.commit()
    trace_and_quarantine(db_session, alert, "analyst")
    db_session.commit()

    quarantines = db_session.execute(
        select(AmountHold).where(AmountHold.kind == HoldKind.QUARANTINE.value)
    ).scalars().all()
    covered = {hold.user_id for hold in quarantines}
    assert hop["id"] in covered
    assert end["id"] in covered
    restriction = db_session.execute(select(AccountRestriction)).scalars().all()
    assert [row.user_id for row in restriction] == [subject["id"]]
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "chain_subject@example.com", "password": "supersecret1"},
    ).json()["access_token"]
    blocked = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": outsider["account_number"],
            "amount": "5.00",
            "pin": "1111",
            "idempotency_key": "restricted-send",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert blocked.status_code == 403
    incoming = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": subject["account_number"],
            "amount": "5.00",
            "pin": "1111",
            "idempotency_key": "still-incoming",
        },
        headers=outsider_headers,
    )
    assert incoming.status_code == 201

    hold = AmountHold(
        user_id=subject["id"],
        alert_id=alert.id,
        amount=Decimal("12.00"),
        status=HoldStatus.CONFIRMED,
        kind=HoldKind.RISK.value,
        reason_codes=["R10"],
        expires_at=now + timedelta(days=1),
        explanation_due_at=now + timedelta(days=1),
    )
    db_session.add(hold)
    db_session.commit()
    assert active_hold_total(db_session, subject["id"]) >= Decimal("12.00")
    del hop_headers


def test_counterfactual_matches_rescore_without_r08():
    raw = [
        {
            "rule_id": "R08",
            "rule_name": "Rapid inbound to outbound",
            "family": "flow",
            "severity": "strong",
            "base_weight": 35,
            "modifier": 0,
            "score_contribution": 35,
            "evidence": {},
        },
        {
            "rule_id": "R05",
            "rule_name": "Unusually large transfer",
            "family": "amount",
            "severity": "medium",
            "base_weight": 25,
            "modifier": 0,
            "score_contribution": 25,
            "evidence": {},
        },
    ]
    trace = _decision_trace(raw, raw, [], 60, "step_up")
    removed = next(item for item in trace["counterfactuals"] if item["removed"] == ["R08"])
    score, action = _rescore(raw, [], {"R08"})
    assert removed["score"] == score
    assert removed["action"] == action
    assert action == ACTION_ALLOW or removed["score"] < 60


def test_pattern_feedback_matches_only_the_same_group(client, db_session, admin_headers):
    user, _ = signup_with_pin(client, "pattern_user@example.com")
    db_session.add(
        CaseEvent(
            alert_id=None,
            kind="review",
            actor="analyst",
            detail={
                "reason": "legitimate_group_payment",
                "subject_user_id": user["id"],
                "sender_ids": [1, 2, 3, 4, 5],
                "onward_recipient_id": 9,
                "families": ["fan", "flow"],
            },
        )
    )
    db_session.commit()
    from app.services.risk.engine import _signatures_match

    same = {
        "sender_ids": [1, 2, 3, 4, 6],
        "onward_recipient_id": 9,
        "families": ["fan", "flow"],
    }
    other = {
        "sender_ids": [8, 7],
        "onward_recipient_id": 9,
        "families": ["fan", "flow"],
    }
    strong_only = {
        "sender_ids": [1, 2, 3, 4, 5],
        "onward_recipient_id": 9,
        "families": ["fan", "flow"],
    }
    assert _signatures_match(
        {"sender_ids": [1, 2, 3, 4, 5], "onward_recipient_id": 9, "families": ["fan", "flow"]},
        same,
    )
    assert not _signatures_match(
        {"sender_ids": [1, 2, 3, 4, 5], "onward_recipient_id": 9, "families": ["fan", "flow"]},
        other,
    )
    assert _signatures_match(
        {"sender_ids": [1, 2, 3, 4, 5], "onward_recipient_id": 9, "families": ["fan", "flow"]},
        strong_only,
    )
    strong_signal = {
        "rule_id": "R08",
        "severity": "strong",
        "family": "flow",
        "score_contribution": 35,
    }
    cleared = [{"check": "reviewed_legitimate_pattern", "cleared": True}]
    breakdown = score([strong_signal], cleared, None)
    assert breakdown["strong"] == 35
    assert breakdown["reductions"] == 10
    assert breakdown["final"] == 35


def test_case_timeline_is_ordered(client, db_session):
    subject, _ = signup_with_pin(client, "case_subject@example.com")
    other, _ = signup_with_pin(client, "case_other@example.com")
    now = datetime.now(UTC)
    tx = Transaction(
        sender_id=other["id"],
        receiver_id=subject["id"],
        amount=Decimal("10.00"),
        status=TransactionStatus.COMPLETED,
        created_at=now,
    )
    db_session.add(tx)
    db_session.flush()
    alert = FraudAlert(
        transaction_id=tx.id,
        user_id=subject["id"],
        subject_user_id=subject["id"],
        risk_score=60,
        triggered_rules=[],
        status=AlertStatus.OPEN,
        tier="suspicious",
        signals=[],
        narrative="Recorded.",
    )
    db_session.add(alert)
    db_session.flush()
    db_session.add(
        RiskEvaluation(
            transaction_id=tx.id,
            subject_user_id=subject["id"],
            subject_role="receiver",
            risk_score=60,
            tier="suspicious",
            signals=[],
            context_checks=[],
            score_breakdown={},
            rules_version="1",
            narrative="Recorded.",
            created_at=now + timedelta(seconds=1),
        )
    )
    db_session.add(
        CaseEvent(
            alert_id=alert.id,
            kind="review",
            actor="analyst",
            detail={"reason": "other"},
            created_at=now + timedelta(seconds=2),
        )
    )
    db_session.commit()
    case = build_case(db_session, alert)
    kinds = [item["kind"] for item in case["timeline"]]
    assert kinds == ["transfer", "evaluation", "review"]
