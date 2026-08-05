"""
Phase 10 tests: PIN brute-force lockout, login rate-limiting, and transfer
atomicity under concurrency (no double-spend, thanks to the Ledger
Service's row-level wallet locking).
"""
from concurrent.futures import ThreadPoolExecutor


def _signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def test_pin_locks_out_after_max_failed_attempts(client):
    """settings.PIN_MAX_ATTEMPTS defaults to 5."""
    alice, alice_headers = _signup_with_pin(client, "alice_lock@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_lock@example.com")

    for _ in range(5):
        response = client.post(
            "/api/v1/transactions/transfer",
            json={
                "recipient_account_number": bob["account_number"],
                "amount": "5.00",
                "pin": "9999",
            },
            headers=alice_headers,
        )
        assert response.status_code == 401

    # 6th attempt, even with the CORRECT pin, must be locked out.
    locked_attempt = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "5.00",
            "pin": "1111",
        },
        headers=alice_headers,
    )
    assert locked_attempt.status_code == 401
    assert "too many incorrect pin attempts" in locked_attempt.json()["detail"].lower()


def test_login_is_rate_limited_after_max_attempts(client):
    """settings.LOGIN_MAX_ATTEMPTS defaults to 10."""
    _signup_with_pin(client, "alice_ratelimit@example.com", password="correcthorse1")

    for _ in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "alice_ratelimit@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "alice_ratelimit@example.com", "password": "correcthorse1"},
    )
    assert limited.status_code == 429


def test_concurrent_transfers_cannot_double_spend(client):
    """
    Alice has exactly 1000 ST. Two concurrent transfers of 700 ST each are
    fired at once; only one can succeed - the Ledger Service's row-level
    wallet locking must serialize them rather than letting both read a
    stale balance and both succeed.
    """
    alice, alice_headers = _signup_with_pin(client, "alice_race@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_race@example.com")

    def attempt_transfer():
        return client.post(
            "/api/v1/transactions/transfer",
            json={
                "recipient_account_number": bob["account_number"],
                "amount": "700.00",
                "pin": "1111",
            },
            headers=alice_headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(attempt_transfer)
        future_b = executor.submit(attempt_transfer)
        response_a = future_a.result()
        response_b = future_b.result()

    statuses = sorted([response_a.status_code, response_b.status_code])
    assert statuses == [201, 422]  # exactly one succeeds, one is rejected as insufficient balance

    final_balance = client.get("/api/v1/auth/me", headers=alice_headers).json()["balance"]
    assert final_balance == "300.00"
