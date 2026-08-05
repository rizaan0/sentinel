"""
Phase 7 tests: Predictive Analytics, ranking users by escalating fraud-
alert frequency/severity trends.
"""
from datetime import datetime, timedelta, timezone

from app.models.fraud_alert import FraudAlert
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


def _trigger_rapid_repeat_alert(client, headers, recipient_account_number, pin="1111"):
    last = None
    for _ in range(3):
        last = client.post(
            "/api/v1/transactions/transfer",
            json={
                "recipient_account_number": recipient_account_number,
                "amount": "10.00",
                "pin": pin,
            },
            headers=headers,
        )
    return last.json()["transaction_id"]


def test_users_with_no_alerts_are_not_predicted(db_session):
    predictions = compute_predictions(db_session)
    assert predictions == []


def test_escalating_user_is_flagged_as_higher_risk_than_a_one_off(client, db_session):
    alice, alice_headers = _signup_with_pin(client, "alice_pred@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_pred@example.com")
    carol, carol_headers = _signup_with_pin(client, "carol_pred@example.com", pin="3333")
    dave, _ = _signup_with_pin(client, "dave_pred@example.com")

    # Alice: escalating pattern - one alert 10 days ago (prior window), then
    # three more alerts this week (last window) => growing frequency.
    old_tx_id = _trigger_rapid_repeat_alert(client, alice_headers, bob["account_number"])
    now = datetime.now(timezone.utc)
    for alert in db_session.query(FraudAlert).join(FraudAlert.transaction).filter(
        FraudAlert.transaction.has(transaction_id=old_tx_id)
    ):
        alert.created_at = now - timedelta(days=10)
        db_session.add(alert)
    db_session.commit()

    for _ in range(2):
        _trigger_rapid_repeat_alert(client, alice_headers, bob["account_number"])

    # Carol: a single one-off alert this week, no prior history (flat, not escalating).
    _trigger_rapid_repeat_alert(client, carol_headers, dave["account_number"], pin="3333")

    predictions = compute_predictions(db_session)
    by_account = {p.user.account_number: p for p in predictions}

    assert alice["account_number"] in by_account
    assert carol["account_number"] in by_account
    assert (
        by_account[alice["account_number"]].trend_score
        > by_account[carol["account_number"]].trend_score
    )


def test_predictions_endpoint_requires_admin(client):
    _, user_headers = _signup_with_pin(client, "notadmin_pred@example.com")
    response = client.get("/api/v1/predictions", headers=user_headers)
    assert response.status_code == 403


def test_predictions_run_and_list_endpoints_work_for_admin(client, admin_headers):
    alice, alice_headers = _signup_with_pin(client, "alice_predapi@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_predapi@example.com")
    _trigger_rapid_repeat_alert(client, alice_headers, bob["account_number"])

    run_response = client.post("/api/v1/predictions/run", headers=admin_headers)
    assert run_response.status_code == 201
    assert len(run_response.json()) >= 1

    list_response = client.get("/api/v1/predictions", headers=admin_headers)
    assert list_response.status_code == 200
    accounts = {p["account_number"] for p in list_response.json()}
    assert alice["account_number"] in accounts
