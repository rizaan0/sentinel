"""
Phase 4 tests: the Rule Engine, fired synchronously by the Monitoring
Engine off the `Transaction Completed Event`, and the admin-only fraud
alert endpoints.
"""


from fraud_helpers import signup_with_pin as _signup_with_pin
from fraud_helpers import transfer as _transfer


def _rule_names(alert_json) -> set[str]:
    return {r["rule_name"] for r in alert_json["triggered_rules"]}


def test_ordinary_transfer_creates_no_alert(client, admin_headers):
    alice, alice_headers = _signup_with_pin(client, "alice_ord@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_ord@example.com")

    response = _transfer(client, alice_headers, bob["account_number"], "50.00", "1111")
    assert response.status_code == 201

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [a for a in alerts if a["transaction_public_id"] == response.json()["transaction_id"]]
    assert matching == []


def test_rapid_same_pair_is_recorded_without_an_alert(client, admin_headers, db_session):
    from test_risk_scenarios import _evaluations

    _, alice_headers = _signup_with_pin(client, "alice_rapid@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_rapid@example.com")

    _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")
    _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")
    third = _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")
    tx_id = third.json()["transaction_id"]

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [a for a in alerts if a["transaction_public_id"] == tx_id]
    assert matching == []
    record = _evaluations(db_session, tx_id)[-1]
    assert any(signal["rule_id"] == "R01" for signal in record.signals)
    assert record.tier == "normal"


def test_circular_fund_flow_is_recorded(client, admin_headers, db_session):
    from test_risk_scenarios import _evaluations

    alice, alice_headers = _signup_with_pin(client, "alice_circ@example.com", pin="1111")
    bob, bob_headers = _signup_with_pin(client, "bob_circ@example.com", pin="2222")
    _, carol_headers = _signup_with_pin(client, "carol_circ@example.com", pin="3333")

    assert _transfer(client, alice_headers, bob["account_number"], "50.00", "1111").status_code == 201
    assert _transfer(client, bob_headers, alice["account_number"], "40.00", "2222").status_code == 201
    # A -> B -> C -> A, with carol funded by bob first.
    carol, carol_headers = _signup_with_pin(client, "carol_circ2@example.com", pin="3333")
    assert _transfer(client, alice_headers, bob["account_number"], "50.00", "1111").status_code == 201
    assert _transfer(client, bob_headers, carol["account_number"], "50.00", "2222").status_code == 201
    closing = _transfer(client, carol_headers, alice["account_number"], "50.00", "3333")
    assert closing.status_code == 201
    tx_id = closing.json()["transaction_id"]

    alerts = [
        a
        for a in client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
        if a["transaction_public_id"] == tx_id
    ]
    assert alerts == []
    record = _evaluations(db_session, tx_id)[-1]
    assert any(signal["rule_id"] == "R09" for signal in record.signals)


def test_fraud_alerts_require_admin(client):
    _, user_headers = _signup_with_pin(client, "notadmin_fraud@example.com")
    response = client.get("/api/v1/fraud-alerts", headers=user_headers)
    assert response.status_code == 403


def test_alert_status_can_be_updated_by_admin(client, admin_headers):
    from test_risk_scenarios import _run_mule

    mule, _ = _run_mule(client, "status")
    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    alert_id = next(a["id"] for a in alerts if a["user_id"] == mule["id"])

    update = client.patch(
        f"/api/v1/fraud-alerts/{alert_id}/status",
        json={"status": "investigating"},
        headers=admin_headers,
    )
    assert update.status_code == 200
    assert update.json()["status"] == "investigating"
