"""
Phase 2 tests: recipient search, transfer execution, history, and receipts.
"""


def _signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def test_search_finds_recipient_by_account_number(client):
    alice, alice_headers = _signup_with_pin(client, "alice_s@example.com")
    bob, _ = _signup_with_pin(client, "bob_s@example.com")

    response = client.get(
        f"/api/v1/transactions/search?account_number={bob['account_number']}",
        headers=alice_headers,
    )
    assert response.status_code == 200
    assert response.json()["account_number"] == bob["account_number"]


def test_search_does_not_return_self(client):
    alice, alice_headers = _signup_with_pin(client, "alice_self@example.com")
    response = client.get(
        f"/api/v1/transactions/search?account_number={alice['account_number']}",
        headers=alice_headers,
    )
    assert response.status_code == 404


def test_search_unknown_account_returns_404(client):
    _, headers = _signup_with_pin(client, "alice_unknown@example.com")
    response = client.get(
        "/api/v1/transactions/search?account_number=000000000000", headers=headers
    )
    assert response.status_code == 404


def test_successful_transfer_updates_both_balances_and_returns_receipt(client):
    alice, alice_headers = _signup_with_pin(client, "alice_t@example.com", pin="1111")
    bob, bob_headers = _signup_with_pin(client, "bob_t@example.com", pin="2222")

    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "150.00",
            "remark": "lunch",
            "pin": "1111",
        },
        headers=alice_headers,
    )
    assert response.status_code == 201
    receipt = response.json()
    assert receipt["direction"] == "sent"
    assert receipt["amount"] == "150.00"
    assert receipt["balance_after"] == "850.00"
    assert receipt["transaction_id"]

    alice_me = client.get("/api/v1/auth/me", headers=alice_headers).json()
    bob_me = client.get("/api/v1/auth/me", headers=bob_headers).json()
    assert alice_me["balance"] == "850.00"
    assert bob_me["balance"] == "1150.00"


def test_transfer_fails_with_wrong_pin(client):
    alice, alice_headers = _signup_with_pin(client, "alice_pin@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_pin@example.com")

    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "10.00",
            "pin": "9999",
        },
        headers=alice_headers,
    )
    assert response.status_code == 401


def test_transfer_fails_with_insufficient_balance(client):
    alice, alice_headers = _signup_with_pin(client, "alice_poor@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_poor@example.com")

    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "999999.00",
            "pin": "1111",
        },
        headers=alice_headers,
    )
    assert response.status_code == 422


def test_transfer_to_unknown_account_returns_404(client):
    _, alice_headers = _signup_with_pin(client, "alice_nowhere@example.com", pin="1111")
    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": "000000000000",
            "amount": "10.00",
            "pin": "1111",
        },
        headers=alice_headers,
    )
    assert response.status_code == 404


def test_self_transfer_is_rejected(client):
    alice, alice_headers = _signup_with_pin(client, "alice_self2@example.com", pin="1111")
    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": alice["account_number"],
            "amount": "10.00",
            "pin": "1111",
        },
        headers=alice_headers,
    )
    assert response.status_code == 400


def test_transfer_requires_pin_to_be_set(client):
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "NoPin",
            "email": "nopin@example.com",
            "password": "supersecret1",
        },
    )
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    bob, _ = _signup_with_pin(client, "bob_nopin@example.com")

    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "10.00",
            "pin": "1234",
        },
        headers=headers,
    )
    assert response.status_code == 401


def test_history_shows_both_sent_and_received_transactions(client):
    alice, alice_headers = _signup_with_pin(client, "alice_h@example.com", pin="1111")
    bob, bob_headers = _signup_with_pin(client, "bob_h@example.com", pin="2222")

    client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "25.00",
            "pin": "1111",
        },
        headers=alice_headers,
    )

    alice_history = client.get("/api/v1/transactions/history", headers=alice_headers).json()
    assert alice_history["total"] == 1
    assert alice_history["items"][0]["direction"] == "sent"

    bob_history = client.get("/api/v1/transactions/history", headers=bob_headers).json()
    assert bob_history["total"] == 1
    assert bob_history["items"][0]["direction"] == "received"


def test_receipt_lookup_is_scoped_to_participants(client):
    alice, alice_headers = _signup_with_pin(client, "alice_r@example.com", pin="1111")
    bob, bob_headers = _signup_with_pin(client, "bob_r@example.com", pin="2222")
    eve, eve_headers = _signup_with_pin(client, "eve_r@example.com", pin="3333")

    transfer = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "5.00",
            "pin": "1111",
        },
        headers=alice_headers,
    ).json()
    tx_id = transfer["transaction_id"]

    assert client.get(f"/api/v1/transactions/{tx_id}", headers=alice_headers).status_code == 200
    assert client.get(f"/api/v1/transactions/{tx_id}", headers=bob_headers).status_code == 200
    assert client.get(f"/api/v1/transactions/{tx_id}", headers=eve_headers).status_code == 404
