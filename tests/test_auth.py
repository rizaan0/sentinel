"""
Phase 1 tests: signup, login, and the Transaction PIN gate.
"""


def _signup(client, email="alice@example.com", password="supersecret1"):
    return client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Alice", "email": email, "password": password},
    )


def test_signup_creates_account_with_initial_balance_and_unique_account_number(client):
    response = _signup(client)
    assert response.status_code == 201

    body = response.json()
    assert body["user"]["account_number"]
    assert len(body["user"]["account_number"]) == 12
    assert body["user"]["balance"] == "1000.00"
    assert body["user"]["pin_is_set"] is False
    assert body["access_token"]


def test_signup_rejects_duplicate_email(client):
    _signup(client, email="dup@example.com")
    response = _signup(client, email="dup@example.com")
    assert response.status_code == 409


def test_two_signups_get_different_account_numbers(client):
    r1 = _signup(client, email="a@example.com")
    r2 = _signup(client, email="b@example.com")
    assert (
        r1.json()["user"]["account_number"] != r2.json()["user"]["account_number"]
    )


def test_login_with_correct_credentials_succeeds(client):
    _signup(client, email="bob@example.com", password="correcthorse1")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "correcthorse1"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "bob@example.com"


def test_login_with_wrong_password_fails(client):
    _signup(client, email="carol@example.com", password="correcthorse1")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_is_case_insensitive_on_email(client):
    _signup(client, email="Case.User@Example.com", password="correcthorse1")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "case.user@example.com", "password": "correcthorse1"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "case.user@example.com"


def test_signup_duplicate_is_case_insensitive(client):
    assert _signup(client, email="Dup.Case@Example.com").status_code == 201
    response = _signup(client, email="dup.case@example.com")
    assert response.status_code == 409


def test_me_requires_bearer_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client):
    token = _signup(client, email="dave@example.com").json()["access_token"]
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "dave@example.com"


def test_pin_status_defaults_to_unset_then_true_after_setup(client):
    token = _signup(client, email="erin@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    status_before = client.get("/api/v1/pin/status", headers=headers)
    assert status_before.json() == {"pin_is_set": False}

    setup = client.post("/api/v1/pin/setup", json={"pin": "1234"}, headers=headers)
    assert setup.status_code == 201
    assert setup.json() == {"pin_is_set": True}

    status_after = client.get("/api/v1/pin/status", headers=headers)
    assert status_after.json() == {"pin_is_set": True}


def test_pin_cannot_be_set_twice(client):
    token = _signup(client, email="frank@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/pin/setup", json={"pin": "1234"}, headers=headers)
    second = client.post("/api/v1/pin/setup", json={"pin": "5678"}, headers=headers)
    assert second.status_code == 409


def test_pin_setup_rejects_non_numeric_pin(client):
    token = _signup(client, email="grace@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/v1/pin/setup", json={"pin": "abcd"}, headers=headers)
    assert response.status_code == 422
