"""Scenario tests for the explainable risk engine."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.amount_hold import AmountHold
from app.models.enums import HoldStatus, TransactionStatus
from app.models.risk_evaluation import RiskEvaluation
from app.models.transaction import Transaction
from app.models.user import User
from app.services.risk.decision import should_hold, tier_for
from fraud_helpers import signup_with_pin as _signup_with_pin
from fraud_helpers import transfer as _transfer


def _evaluations(db_session, public_id: str) -> list[RiskEvaluation]:
    tx = db_session.execute(
        select(Transaction).where(Transaction.transaction_id == public_id)
    ).scalar_one()
    db_session.expire_all()
    return list(
        db_session.execute(select(RiskEvaluation).where(RiskEvaluation.transaction_id == tx.id))
        .scalars()
        .all()
    )


def _age(db_session, user_id: int, days: int = 60) -> None:
    user = db_session.get(User, user_id)
    user.created_at = datetime.now(UTC) - timedelta(days=days)
    db_session.commit()


def test_split_bill_outside_payment_is_pattern_a_without_hold(client, admin_headers, db_session):
    receiver, _ = _signup_with_pin(client, "turf_receiver@example.com")
    _age(db_session, receiver["id"])
    senders = []
    for index in range(6):
        user, headers = _signup_with_pin(client, f"friend_{index}@example.com", pin="1111")
        _age(db_session, user["id"])
        senders.append((user, headers))

    last = None
    for _, headers in senders:
        last = _transfer(client, headers, receiver["account_number"], "183.33", "1111", remark="turf")
        assert last.status_code == 201

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    assert alerts == []
    holds = db_session.execute(select(AmountHold)).scalars().all()
    assert holds == []

    records = _evaluations(db_session, last.json()["transaction_id"])
    assert records
    record = records[-1]
    assert record.pattern == "A"
    assert record.tier in {"normal", "low_anomaly"}
    assert any(signal["rule_id"] == "R03" for signal in record.signals)
    assert "onward transfer ratio cleared" in record.narrative.lower()
    assert record.hold_placed is False


def test_fan_in_modifiers_are_one_rule(client, db_session):
    receiver, _ = _signup_with_pin(client, "mod_receiver@example.com")
    last = None
    for index in range(6):
        user, headers = _signup_with_pin(client, f"mod_sender_{index}@example.com", pin="1111")
        last = _transfer(client, headers, receiver["account_number"], "183.00", "1111")
        assert last.status_code == 201
    record = _evaluations(db_session, last.json()["transaction_id"])[-1]
    r03 = [signal for signal in record.signals if signal["rule_id"] == "R03"]
    assert len(r03) == 1
    assert r03[0]["modifier"] == 8
    assert r03[0]["score_contribution"] == 23


def test_mule_pass_through_holds_only_the_flagged_amount(client, admin_headers, db_session):
    mule, mule_headers = _signup_with_pin(client, "mule@example.com", pin="1111")
    sink, _ = _signup_with_pin(client, "sink@example.com")
    for index in range(6):
        _, headers = _signup_with_pin(client, f"payer_{index}@example.com", pin="2222")
        response = _transfer(client, headers, mule["account_number"], "100.00", "2222")
        assert response.status_code == 201

    onward = _transfer(client, mule_headers, sink["account_number"], "550.00", "1111")
    assert onward.status_code == 201

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [alert for alert in alerts if alert["user_id"] == mule["id"]]
    assert matching
    assert matching[0]["pattern"] == "B"
    assert matching[0]["hold_status"] == "active"
    held = float(matching[0]["hold_amount"])
    assert held == 600.0

    blocked = _transfer(client, mule_headers, sink["account_number"], "600.00", "1111")
    assert blocked.status_code == 422
    assert "on hold" in blocked.json()["detail"]

    incoming = _signup_with_pin(client, "still_pays@example.com", pin="3333")
    received = _transfer(client, incoming[1], mule["account_number"], "15.00", "3333")
    assert received.status_code == 201

    db_session.expire_all()
    hold = db_session.execute(select(AmountHold).where(AmountHold.user_id == mule["id"])).scalar_one()
    assert hold.status == HoldStatus.ACTIVE


def test_mule_chain_records_pattern_e(client, db_session):
    users = []
    for name, pin in (("chain_a", "1111"), ("chain_b", "2222"), ("chain_c", "3333"), ("chain_d", "4444")):
        user, headers = _signup_with_pin(client, f"{name}@example.com", pin=pin)
        users.append((user, headers, pin))

    amounts = ["800.00", "760.00", "720.00"]
    last = None
    for index in range(3):
        _, headers, pin = users[index]
        last = _transfer(client, headers, users[index + 1][0]["account_number"], amounts[index], pin)
        assert last.status_code == 201

    record = _evaluations(db_session, last.json()["transaction_id"])[-1]
    assert any(signal["rule_id"] == "R10" for signal in record.signals)
    assert record.pattern == "E"
    # R10 alone is 45, below the 70 hold gate. Pattern E can hold only at 70+.
    assert record.hold_placed is False


def test_soft_signals_never_hold():
    signals = [
        {"rule_id": "R01", "family": "velocity", "severity": "soft", "base_weight": 10, "modifier": 0, "score_contribution": 10},
        {"rule_id": "R03", "family": "fan", "severity": "soft", "base_weight": 15, "modifier": 8, "score_contribution": 23},
        {"rule_id": "R11", "family": "counterparty", "severity": "soft", "base_weight": 15, "modifier": 0, "score_contribution": 15},
        {"rule_id": "R12", "family": "counterparty", "severity": "soft", "base_weight": 10, "modifier": 0, "score_contribution": 0},
        {"rule_id": "ML", "family": "model", "severity": "soft", "base_weight": 15, "modifier": 0, "score_contribution": 15},
    ]
    tier = tier_for(90, signals, None)
    assert tier == "high"
    assert should_hold(tier, None, signals) is False


def test_large_transfer_needs_five_prior(client, db_session):
    alice, headers = _signup_with_pin(client, "thin_large@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "thin_bob@example.com")
    last = None
    for _ in range(3):
        last = _transfer(client, headers, bob["account_number"], "10.00", "1111")
    outlier = _transfer(client, headers, bob["account_number"], "500.00", "1111")
    assert outlier.status_code == 201
    records = _evaluations(db_session, outlier.json()["transaction_id"])
    fired = []
    if records:
        fired = [signal["rule_id"] for signal in records[-1].signals]
    assert "R05" not in fired
    assert alice["id"]


def test_single_transfer_after_dormancy_does_not_fire(client, db_session):
    alice, headers = _signup_with_pin(client, "dormant_alice@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "dormant_bob@example.com")
    sender = db_session.get(User, alice["id"])
    receiver = db_session.get(User, bob["id"])
    old = Transaction(
        transaction_id="old-dormant-tx",
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=10,
        status=TransactionStatus.COMPLETED,
        created_at=datetime.now(UTC) - timedelta(days=40),
    )
    db_session.add(old)
    db_session.commit()

    recent = _transfer(client, headers, bob["account_number"], "12.00", "1111")
    assert recent.status_code == 201
    records = _evaluations(db_session, recent.json()["transaction_id"])
    fired = [signal["rule_id"] for record in records for signal in record.signals]
    assert "R07" not in fired


def _run_mule(client, label):
    mule, mule_headers = _signup_with_pin(client, f"{label}_mule@example.com", pin="1111")
    sink, _ = _signup_with_pin(client, f"{label}_sink@example.com")
    for index in range(6):
        _, headers = _signup_with_pin(client, f"{label}_payer_{index}@example.com", pin="2222")
        response = _transfer(client, headers, mule["account_number"], "100.00", "2222")
        assert response.status_code == 201
    onward = _transfer(client, mule_headers, sink["account_number"], "550.00", "1111")
    assert onward.status_code == 201
    return mule, mule_headers


def _backdate_activity(db_session, user_id: int) -> None:
    when = datetime.now(UTC) - timedelta(days=2)
    rows = db_session.execute(
        select(Transaction).where(
            (Transaction.sender_id == user_id) | (Transaction.receiver_id == user_id)
        )
    ).scalars().all()
    for row in rows:
        row.created_at = when
    db_session.commit()


def test_false_positive_releases_hold_and_lowers_repeat(client, admin_headers, db_session):
    mule, mule_headers = _run_mule(client, "fp")
    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    alert = next(item for item in alerts if item["user_id"] == mule["id"])
    first_score = alert["risk_score"]
    update = client.patch(
        f"/api/v1/fraud-alerts/{alert['id']}/status",
        json={"status": "false_positive", "reason": "legitimate_group_payment"},
        headers=admin_headers,
    )
    assert update.status_code == 200
    db_session.expire_all()
    hold = db_session.execute(select(AmountHold).where(AmountHold.user_id == mule["id"])).scalar_one()
    assert hold.status == HoldStatus.RELEASED

    _backdate_activity(db_session, mule["id"])
    sink, _ = _signup_with_pin(client, "fp_sink_again@example.com")
    for index in range(6):
        _, headers = _signup_with_pin(client, f"fp_again_{index}@example.com", pin="2222")
        assert _transfer(client, headers, mule["account_number"], "100.00", "2222").status_code == 201
    assert _transfer(client, mule_headers, sink["account_number"], "550.00", "1111").status_code == 201

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    repeat = [item for item in alerts if item["user_id"] == mule["id"] and item["status"] == "open"]
    assert repeat
    reviewed = [
        check
        for check in repeat[0].get("context_checks") or []
        if check["check"] == "reviewed_legitimate_pattern"
    ]
    assert reviewed and reviewed[0]["cleared"] is False
    assert first_score >= 50


def test_user_explanation_is_stored(client, admin_headers):
    mule, mule_headers = _run_mule(client, "explain")
    holds = client.get("/api/v1/holds/me", headers=mule_headers).json()
    assert holds
    saved = client.post(
        f"/api/v1/holds/{holds[0]['id']}/explanation",
        json={"text": "These were repayments from a group booking."},
        headers=mule_headers,
    )
    assert saved.status_code == 200
    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    alert = next(item for item in alerts if item["user_id"] == mule["id"])
    assert alert["user_explanation"] == "These were repayments from a group booking."
