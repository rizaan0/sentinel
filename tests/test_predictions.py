"""
Phase 7 tests: Predictive Analytics, ranking users by escalating fraud-
alert frequency/severity trends.
"""
from datetime import datetime, timedelta, timezone

from app.models.enums import AlertStatus
from app.models.fraud_alert import FraudAlert
from app.models.transaction import Transaction
from app.services.prediction_service import compute_predictions


def _signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def _seed_alert(db_session, client, headers, recipient_account_number, user_id, pin="1111", when=None, score=40):
    response = client.post(
        "/api/v1/transactions/transfer",
        json={"recipient_account_number": recipient_account_number, "amount": "10.00", "pin": pin},
        headers=headers,
    )
    tx = db_session.query(Transaction).filter(
        Transaction.transaction_id == response.json()["transaction_id"]
    ).one()
    alert = FraudAlert(
        transaction_id=tx.id,
        user_id=user_id,
        risk_score=score,
        triggered_rules=[{"rule_name": "R03", "explanation": "fan-in", "risk_weight": 15}],
        status=AlertStatus.OPEN,
        tier="suspicious",
    )
    db_session.add(alert)
    db_session.flush()
    if when is not None:
        alert.created_at = when
    db_session.commit()
    return response.json()["transaction_id"]


def test_users_with_no_alerts_are_not_predicted(db_session):
    predictions = compute_predictions(db_session)
    assert predictions == []


def test_escalating_user_is_flagged_as_higher_risk_than_a_one_off(client, db_session):
    alice, alice_headers = _signup_with_pin(client, "alice_pred@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_pred@example.com")
    carol, carol_headers = _signup_with_pin(client, "carol_pred@example.com", pin="3333")
    dave, _ = _signup_with_pin(client, "dave_pred@example.com")

    now = datetime.now(timezone.utc)
    _seed_alert(
        db_session, client, alice_headers, bob["account_number"], alice["id"],
        when=now - timedelta(days=10), score=40,
    )
    for _ in range(3):
        _seed_alert(db_session, client, alice_headers, bob["account_number"], alice["id"], score=70)

    _seed_alert(
        db_session, client, carol_headers, dave["account_number"], carol["id"], pin="3333", score=40,
    )

    predictions = compute_predictions(db_session)
    by_account = {p.user.account_number: p for p in predictions}

    assert alice["account_number"] in by_account
    assert carol["account_number"] in by_account
    alice_row = by_account[alice["account_number"]]
    carol_row = by_account[carol["account_number"]]
    assert alice_row.trend_score > carol_row.trend_score
    assert alice_row.predicted_7d_risk >= alice_row.current_risk
    assert len(alice_row.series) == 14
    assert "over the next 7 days" in alice_row.explanation
    assert "confidence" not in alice_row.explanation.lower()


def test_predictions_endpoint_requires_admin(client):
    _, user_headers = _signup_with_pin(client, "notadmin_pred@example.com")
    response = client.get("/api/v1/predictions", headers=user_headers)
    assert response.status_code == 403


def test_predictions_run_and_list_endpoints_work_for_admin(client, admin_headers, db_session):
    alice, alice_headers = _signup_with_pin(client, "alice_predapi@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_predapi@example.com")
    _seed_alert(db_session, client, alice_headers, bob["account_number"], alice["id"])

    run_response = client.post("/api/v1/predictions/run", headers=admin_headers)
    assert run_response.status_code == 201
    assert len(run_response.json()) >= 1

    list_response = client.get("/api/v1/predictions", headers=admin_headers)
    assert list_response.status_code == 200
    body = list_response.json()
    accounts = {p["account_number"] for p in body}
    assert alice["account_number"] in accounts
    row = next(item for item in body if item["account_number"] == alice["account_number"])
    assert "current_risk" in row
    assert "predicted_7d_risk" in row
    assert "explanation" in row
    assert "confidence" not in row
