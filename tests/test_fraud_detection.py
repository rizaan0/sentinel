"""
Phase 4 tests: the Rule Engine, fired synchronously by the Monitoring
Engine off the `Transaction Completed Event`, and the admin-only fraud
alert endpoints.
"""


def _signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def _transfer(client, headers, recipient_account_number, amount, pin, remark=None):
    return client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": recipient_account_number,
            "amount": amount,
            "remark": remark,
            "pin": pin,
        },
        headers=headers,
    )


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


def test_rapid_repeated_transfers_triggers_alert(client, admin_headers):
    alice, alice_headers = _signup_with_pin(client, "alice_rapid@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_rapid@example.com")

    _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")
    _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")
    third = _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")
    tx_id = third.json()["transaction_id"]

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [a for a in alerts if a["transaction_public_id"] == tx_id]
    assert len(matching) == 1
    assert "rapid_repeated_transfers" in _rule_names(matching[0])
    assert matching[0]["status"] == "open"
    assert matching[0]["risk_score"] > 0


def test_circular_fund_flow_triggers_alert(client, admin_headers):
    alice, alice_headers = _signup_with_pin(client, "alice_circ@example.com", pin="1111")
    bob, bob_headers = _signup_with_pin(client, "bob_circ@example.com", pin="2222")
    carol, carol_headers = _signup_with_pin(client, "carol_circ@example.com", pin="3333")

    _transfer(client, alice_headers, bob["account_number"], "50.00", "1111")
    _transfer(client, bob_headers, carol["account_number"], "50.00", "2222")
    closing = _transfer(client, carol_headers, alice["account_number"], "50.00", "3333")
    tx_id = closing.json()["transaction_id"]

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [a for a in alerts if a["transaction_public_id"] == tx_id]
    assert len(matching) == 1
    assert "circular_fund_flow" in _rule_names(matching[0])


def test_unusually_large_transfer_triggers_alert(client, admin_headers):
    alice, alice_headers = _signup_with_pin(client, "alice_large@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_large@example.com")

    # Build a consistent small-transfer history.
    for _ in range(3):
        _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")

    outlier = _transfer(client, alice_headers, bob["account_number"], "500.00", "1111")
    tx_id = outlier.json()["transaction_id"]

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [a for a in alerts if a["transaction_public_id"] == tx_id]
    assert len(matching) == 1
    assert "unusually_large_transfer" in _rule_names(matching[0])


def test_burst_of_small_transactions_triggers_alert(client, admin_headers):
    alice, alice_headers = _signup_with_pin(client, "alice_burst@example.com", pin="1111")
    recipients = []
    for i in range(5):
        recipient, _ = _signup_with_pin(client, f"burst_recipient_{i}@example.com")
        recipients.append(recipient)

    last_response = None
    for recipient in recipients:
        last_response = _transfer(client, alice_headers, recipient["account_number"], "10.00", "1111")

    tx_id = last_response.json()["transaction_id"]
    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [a for a in alerts if a["transaction_public_id"] == tx_id]
    assert len(matching) == 1
    assert "burst_of_small_transactions" in _rule_names(matching[0])


def test_fraud_alerts_require_admin(client):
    _, user_headers = _signup_with_pin(client, "notadmin_fraud@example.com")
    response = client.get("/api/v1/fraud-alerts", headers=user_headers)
    assert response.status_code == 403


def test_alert_status_can_be_updated_by_admin(client, admin_headers):
    alice, alice_headers = _signup_with_pin(client, "alice_status@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_status@example.com")

    for _ in range(3):
        response = _transfer(client, alice_headers, bob["account_number"], "10.00", "1111")
    tx_id = response.json()["transaction_id"]

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    alert_id = next(a["id"] for a in alerts if a["transaction_public_id"] == tx_id)

    update = client.patch(
        f"/api/v1/fraud-alerts/{alert_id}/status",
        json={"status": "investigating"},
        headers=admin_headers,
    )
    assert update.status_code == 200
    assert update.json()["status"] == "investigating"
