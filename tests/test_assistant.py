"""
Phase 8 tests: the Retrieval Service (RAG), and the AI Investigation
Assistant endpoint. The Ollama call itself is monkeypatched so tests stay
fast/deterministic and don't require a running local LLM.
"""
from app.services import ai_assistant_service, ollama_client, retrieval_service


def _signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def test_build_context_for_transaction_includes_alerts_and_history(client, db_session):
    alice, alice_headers = _signup_with_pin(client, "alice_ctx@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_ctx@example.com")

    # Three rapid transfers to trigger a fraud alert.
    last = None
    for _ in range(3):
        last = client.post(
            "/api/v1/transactions/transfer",
            json={"recipient_account_number": bob["account_number"], "amount": "10.00", "pin": "1111"},
            headers=alice_headers,
        )

    from app.models.transaction import Transaction

    tx = db_session.query(Transaction).filter(
        Transaction.transaction_id == last.json()["transaction_id"]
    ).one()

    context = retrieval_service.build_context_for_transaction(db_session, tx)
    assert context["transaction"]["transaction_id"] == tx.transaction_id
    assert len(context["fraud_alerts"]) == 1
    assert context["fraud_alerts"][0]["risk_score"] > 0
    assert len(context["sender_recent_history"]) == 3
    assert "reconciliation_reports" in context


def test_build_context_for_account_returns_error_for_unknown_account(db_session):
    context = retrieval_service.build_context_for_account(db_session, "000000000000")
    assert "error" in context


def test_assistant_endpoint_requires_admin(client):
    _, user_headers = _signup_with_pin(client, "notadmin_ai@example.com")
    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "why?", "account_number": "000000000000"},
        headers=user_headers,
    )
    assert response.status_code == 403


def test_assistant_requires_a_target(client, admin_headers):
    response = client.post(
        "/api/v1/assistant/ask", json={"question": "why?"}, headers=admin_headers
    )
    assert response.status_code == 422


def test_assistant_returns_404_for_unknown_transaction(client, admin_headers):
    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "why?", "transaction_id": "not-a-real-id"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_assistant_answers_and_logs_the_interaction(client, admin_headers, monkeypatch, db_session):
    monkeypatch.setattr(
        ai_assistant_service,
        "chat",
        lambda system_prompt, user_prompt: "This transaction was flagged due to rapid repeats.",
    )

    alice, alice_headers = _signup_with_pin(client, "alice_ai@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_ai@example.com")
    for _ in range(3):
        last = client.post(
            "/api/v1/transactions/transfer",
            json={"recipient_account_number": bob["account_number"], "amount": "10.00", "pin": "1111"},
            headers=alice_headers,
        )
    tx_id = last.json()["transaction_id"]

    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Why was this flagged?", "transaction_id": tx_id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "rapid repeats" in body["answer"]
    assert body["question"] == "Why was this flagged?"

    from app.models.ai_assistant_log import AiAssistantLog

    log_row = db_session.get(AiAssistantLog, body["id"])
    assert log_row is not None
    assert log_row.answer == body["answer"]
    assert log_row.context_used["transaction"]["transaction_id"] == tx_id


def test_assistant_returns_503_when_ollama_unavailable(client, admin_headers, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise ollama_client.OllamaUnavailableError("Ollama is not running")

    monkeypatch.setattr(ai_assistant_service, "chat", _raise)

    alice, alice_headers = _signup_with_pin(client, "alice_aidown@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_aidown@example.com")
    client.post(
        "/api/v1/transactions/transfer",
        json={"recipient_account_number": bob["account_number"], "amount": "10.00", "pin": "1111"},
        headers=alice_headers,
    )

    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "why?", "account_number": alice["account_number"]},
        headers=admin_headers,
    )
    assert response.status_code == 503
