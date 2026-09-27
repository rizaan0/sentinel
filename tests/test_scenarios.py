"""Scenario runner uses the fixed cast and only real transfers create alerts."""

from sqlalchemy import func, select

from app.models.amount_hold import AmountHold
from app.models.enums import AlertStatus
from app.models.fraud_alert import FraudAlert
from app.models.reconciliation_report import ReconciliationReport
from app.models.transaction import Transaction
from app.models.user import User
from app.services.scenarios import runner
from app.services.scenarios.cast import MEMBERS, cast_size, ensure_cast
from app.services.scenarios.runner import ScenarioBusyError, current_status, start_scenario, stop_scenario


def _wait():
    assert runner._thread is not None
    runner._thread.join(timeout=90)
    assert not runner._thread.is_alive()


def _alerts_for(db_session, account_number: str) -> list[FraudAlert]:
    user = db_session.execute(
        select(User).where(User.account_number == account_number)
    ).scalar_one()
    db_session.expire_all()
    return list(
        db_session.execute(select(FraudAlert).where(FraudAlert.user_id == user.id)).scalars().all()
    )


def test_cast_reuses_the_same_eight_account_numbers(db_session):
    first = ensure_cast(db_session)
    second = ensure_cast(db_session)
    assert cast_size(db_session) == 8
    assert [user.account_number for user in first.values()] == [number for _, _, _, number in MEMBERS]
    assert [user.id for user in first.values()] == [user.id for user in second.values()]
    users = db_session.execute(select(func.count()).select_from(User)).scalar_one()
    assert users == 8


def test_normal_scenario_creates_real_transfers(client, admin_headers, db_session):
    before = db_session.execute(select(func.count()).select_from(Transaction)).scalar_one()
    start_scenario("normal", delay_seconds=0)
    _wait()
    assert current_status().state == "finished"
    db_session.expire_all()
    after = db_session.execute(select(func.count()).select_from(Transaction)).scalar_one()
    assert after >= before + 3
    listed = client.get("/api/v1/fraud-alerts", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_split_bill_scenario_does_not_place_a_hold(client, admin_headers, db_session):
    start_scenario("split_bill", delay_seconds=0)
    _wait()
    assert current_status().state == "finished"
    db_session.expire_all()
    receiver = db_session.execute(
        select(User).where(User.account_number == "100000000002")
    ).scalar_one()
    holds = db_session.execute(
        select(AmountHold).where(AmountHold.user_id == receiver.id)
    ).scalars().all()
    assert holds == []
    listed = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    assert listed == []


def test_pass_through_creates_a_high_alert(db_session):
    start_scenario("pass_through", delay_seconds=0)
    _wait()
    assert current_status().state == "finished"
    db_session.expire_all()
    alerts = _alerts_for(db_session, "100000000003")
    assert alerts
    assert max(alert.risk_score for alert in alerts) >= 70


def test_large_fan_creates_a_lower_alert_than_pass_through(db_session):
    start_scenario("large", delay_seconds=0)
    _wait()
    assert current_status().state == "finished"
    db_session.expire_all()
    alerts = _alerts_for(db_session, "100000000003")
    assert alerts
    score = max(alert.risk_score for alert in alerts)
    assert score >= 50
    assert score < 90


def test_legacy_low_score_alert_is_hidden(client, admin_headers, db_session):
    start_scenario("normal", delay_seconds=0)
    _wait()
    db_session.expire_all()
    meera = db_session.execute(
        select(User).where(User.account_number == "100000000001")
    ).scalar_one()
    transaction = db_session.execute(
        select(Transaction).where(Transaction.sender_id == meera.id)
    ).scalars().first()
    db_session.add(
        FraudAlert(
            transaction_id=transaction.id,
            user_id=meera.id,
            risk_score=25,
            triggered_rules=[{"rule_name": "R05", "explanation": "old", "risk_weight": 25}],
            status=AlertStatus.OPEN,
            tier="low_anomaly",
        )
    )
    db_session.commit()
    listed = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    assert all(item["risk_score"] >= 50 for item in listed)
    assert all(item["id"] != transaction.id or item["risk_score"] != 25 for item in listed)
    visible_ids = {item["user_id"] for item in listed}
    assert meera.id not in visible_ids


def test_reconciliation_scenario_changes_which_accounts_are_out_of_balance(db_session):
    start_scenario("reconciliation", delay_seconds=0)
    _wait()
    assert current_status().state == "finished"
    db_session.expire_all()
    reports = list(
        db_session.execute(select(ReconciliationReport).order_by(ReconciliationReport.id)).scalars().all()
    )
    assert [report.discrepancy_count for report in reports] == [0, 1, 2, 0]
    assert reports[0].accounts_checked == 8
    assert reports[1].discrepancies[0]["account_number"] == "100000000008"
    assert {row["account_number"] for row in reports[2].discrepancies} == {
        "100000000007",
        "100000000008",
    }
    assert reports[-1].status.value == "clean"


def test_second_scenario_is_rejected_while_one_is_running():
    start_scenario("large", delay_seconds=2)
    try:
        try:
            start_scenario("normal", delay_seconds=0)
            raised = False
        except ScenarioBusyError:
            raised = True
        assert raised
    finally:
        stop_scenario()
        _wait()


def test_start_unknown_scenario_is_404(client, admin_headers):
    response = client.post("/api/v1/admin/scenarios/missing/start", headers=admin_headers)
    assert response.status_code == 404
