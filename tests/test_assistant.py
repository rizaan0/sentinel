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

    from app.models.enums import AlertStatus
    from app.models.fraud_alert import FraudAlert

    db_session.add(
        FraudAlert(
            transaction_id=tx.id,
            user_id=alice["id"],
            risk_score=55,
            triggered_rules=[{"rule_name": "R03", "explanation": "fan-in", "risk_weight": 15}],
            status=AlertStatus.OPEN,
            tier="suspicious",
            pattern="A",
            signals=[{"rule_id": "R03", "explanation": "fan-in", "score_contribution": 15}],
            context_checks=[{"check": "onward_transfer_ratio", "cleared": True}],
            narrative="Risk score: 55/100.",
        )
    )
    db_session.commit()

    context = retrieval_service.build_context_for_transaction(db_session, tx)
    assert context["transaction"]["transaction_id"] == tx.transaction_id
    assert len(context["fraud_alerts"]) == 1
    assert context["fraud_alerts"][0]["risk_score"] > 0
    assert context["fraud_alerts"][0]["signals"][0]["rule_id"] == "R03"
    assert context["fraud_alerts"][0]["context_checks"][0]["cleared"] is True
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
        lambda system_prompt, user_prompt, history=None: "This transaction was flagged due to rapid repeats.",
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


def test_model_refusal_is_replaced_with_the_recorded_explanation(
    client, admin_headers, monkeypatch, db_session
):
    monkeypatch.setattr(
        ai_assistant_service,
        "chat",
        lambda system_prompt, user_prompt, history=None: (
            "I cannot provide a response that contains information about how to commit fraud."
        ),
    )
    alice, alice_headers = _signup_with_pin(client, "alice_refuse@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_refuse@example.com")
    transfer = client.post(
        "/api/v1/transactions/transfer",
        json={"recipient_account_number": bob["account_number"], "amount": "20.00", "pin": "1111"},
        headers=alice_headers,
    )
    from app.models.enums import AlertStatus
    from app.models.fraud_alert import FraudAlert
    from app.models.transaction import Transaction

    tx = db_session.query(Transaction).filter(
        Transaction.transaction_id == transfer.json()["transaction_id"]
    ).one()
    db_session.add(
        FraudAlert(
            transaction_id=tx.id,
            user_id=alice["id"],
            risk_score=78,
            triggered_rules=[{"rule_name": "R03", "explanation": "fan-in", "risk_weight": 23}],
            status=AlertStatus.OPEN,
            tier="high",
            pattern="B",
            signals=[
                {
                    "rule_id": "R03",
                    "rule_name": "Fan-In Burst",
                    "score_contribution": 23,
                    "explanation": "6 distinct accounts sent funds within 2 minutes.",
                }
            ],
            context_checks=[{"check": "onward_transfer_ratio", "cleared": False}],
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "why is it in the fraud section?", "transaction_id": tx.transaction_id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "Fan-In Burst rule triggered" in answer
    assert "R03" in answer
    assert "78" in answer
    assert "cannot provide" not in answer.lower()


def test_follow_up_uses_conversation_and_answers_the_new_question(
    client, admin_headers, monkeypatch, db_session
):
    calls = []

    def _chat(system_prompt, user_prompt, history=None):
        calls.append({"prompt": user_prompt, "history": history or []})
        if len(calls) == 1:
            return "Six accounts sent similar amounts within two minutes. That is why it was flagged."
        return (
            "No. Do not block the whole account. The recorded score is 78 and this result "
            "did not freeze the account. You still make the final call."
        )

    monkeypatch.setattr(ai_assistant_service, "chat", _chat)
    alice, alice_headers = _signup_with_pin(client, "alice_chat@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_chat@example.com")
    transfer = client.post(
        "/api/v1/transactions/transfer",
        json={"recipient_account_number": bob["account_number"], "amount": "20.00", "pin": "1111"},
        headers=alice_headers,
    )
    from app.models.enums import AlertStatus
    from app.models.fraud_alert import FraudAlert
    from app.models.transaction import Transaction

    tx = db_session.query(Transaction).filter(
        Transaction.transaction_id == transfer.json()["transaction_id"]
    ).one()
    db_session.add(
        FraudAlert(
            transaction_id=tx.id,
            user_id=alice["id"],
            risk_score=78,
            triggered_rules=[{"rule_name": "R03", "explanation": "fan-in", "risk_weight": 23}],
            status=AlertStatus.OPEN,
            tier="high",
            signals=[
                {
                    "rule_id": "R03",
                    "rule_name": "Fan-In Burst",
                    "score_contribution": 23,
                    "explanation": "6 distinct accounts sent funds within 2 minutes.",
                }
            ],
            context_checks=[],
        )
    )
    db_session.commit()

    first = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Why is it in the fraud section?", "transaction_id": tx.transaction_id},
        headers=admin_headers,
    )
    second = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Should I block this account?", "transaction_id": tx.transaction_id},
        headers=admin_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert "block" in second.json()["answer"].lower()
    assert "Fan-In Burst rule triggered" not in second.json()["answer"]
    assert calls[1]["history"][0]["content"] == "Why is it in the fraud section?"
    assert "similar amounts" in calls[1]["history"][1]["content"]
    assert "Recorded result" not in calls[1]["prompt"]


def test_repeated_model_reply_is_replaced_with_an_answer_to_the_question(
    client, admin_headers, monkeypatch, db_session
):
    repeated = (
        "The ML Anomaly Detector flagged this transaction as statistically unusual "
        "for the sender's account. Context checks reduced the significance of the pattern, "
        "leaving the risk score at 35 in the lower risk tier."
    )

    def _chat(system_prompt, user_prompt, history=None):
        return repeated

    monkeypatch.setattr(ai_assistant_service, "chat", _chat)
    alice, alice_headers = _signup_with_pin(client, "alice_repeat@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_repeat@example.com")
    transfer = client.post(
        "/api/v1/transactions/transfer",
        json={"recipient_account_number": bob["account_number"], "amount": "15.00", "pin": "1111"},
        headers=alice_headers,
    )
    from app.models.enums import AlertStatus
    from app.models.fraud_alert import FraudAlert
    from app.models.transaction import Transaction

    tx = db_session.query(Transaction).filter(
        Transaction.transaction_id == transfer.json()["transaction_id"]
    ).one()
    db_session.add(
        FraudAlert(
            transaction_id=tx.id,
            user_id=alice["id"],
            risk_score=35,
            triggered_rules=[{"rule_name": "ML", "explanation": "anomaly", "risk_weight": 15}],
            status=AlertStatus.OPEN,
            tier="low_anomaly",
            signals=[
                {
                    "rule_id": "ML",
                    "rule_name": "ML Anomaly",
                    "score_contribution": 15,
                    "explanation": "The model flagged this transfer as unusual.",
                }
            ],
            context_checks=[],
        )
    )
    db_session.commit()
    client.post(
        "/api/v1/assistant/ask",
        json={"question": "Why is it in the fraud section?", "transaction_id": tx.transaction_id},
        headers=admin_headers,
    )
    second = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Should I block or keep it open?", "transaction_id": tx.transaction_id},
        headers=admin_headers,
    )
    assert second.status_code == 200
    answer = second.json()["answer"].lower()
    assert "keep the case open" in answer
    assert "do not block the whole account" in answer
    assert "statistically unusual" not in answer
