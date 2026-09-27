"""
Phase 6 tests: online feature extraction and the ML Anomaly Detector's
integration into the Monitoring Engine (using a fake model artifact so
tests stay fast/deterministic and don't depend on a real trained model).
"""
from app.services import ml_anomaly_service, ml_features


def _signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def test_extract_features_returns_expected_columns_and_values(client, db_session):
    alice, alice_headers = _signup_with_pin(client, "alice_feat@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_feat@example.com")

    from app.models.transaction import Transaction

    client.post(
        "/api/v1/transactions/transfer",
        json={"recipient_account_number": bob["account_number"], "amount": "30.00", "pin": "1111"},
        headers=alice_headers,
    )

    tx = db_session.query(Transaction).filter(Transaction.sender_id == alice["id"]).one()
    features = ml_features.extract_features(db_session, tx)

    assert len(features) == len(ml_features.FEATURE_COLUMNS)
    amount_idx = ml_features.FEATURE_COLUMNS.index("amount")
    assert features[amount_idx] == 30.0
    # No prior history for alice yet, so her own baseline average is 0.
    avg_idx = ml_features.FEATURE_COLUMNS.index("sender_avg_amount_30d")
    assert features[avg_idx] == 0.0


def test_ml_anomaly_service_returns_none_without_a_trained_model(monkeypatch, tmp_path):
    # Force a definitely-nonexistent artifact path, regardless of whether a
    # real model has been trained on this machine (e.g. via ml/train_model.py).
    monkeypatch.setattr(ml_anomaly_service, "ARTIFACT_PATH", tmp_path / "no_such_model.joblib")
    ml_anomaly_service.reset_cache()
    assert ml_anomaly_service._load_artifact() is None  # noqa: SLF001


class _FakeAlwaysAnomalous:
    def predict(self, _x):
        return [-1]

    def decision_function(self, _x):
        return [-0.42]


def test_monitoring_engine_creates_ml_alert_when_model_flags_anomaly(
    client, admin_headers, monkeypatch, db_session
):
    fake_artifact = {"model": _FakeAlwaysAnomalous(), "feature_columns": ml_features.FEATURE_COLUMNS}
    monkeypatch.setattr(ml_anomaly_service, "_load_artifact", lambda: fake_artifact)

    alice, alice_headers = _signup_with_pin(client, "alice_ml@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_ml@example.com")

    response = client.post(
        "/api/v1/transactions/transfer",
        json={"recipient_account_number": bob["account_number"], "amount": "15.00", "pin": "1111"},
        headers=alice_headers,
    )
    tx_id = response.json()["transaction_id"]

    from sqlalchemy import select

    from app.models.risk_evaluation import RiskEvaluation
    from app.models.transaction import Transaction

    alerts = client.get("/api/v1/fraud-alerts", headers=admin_headers).json()
    matching = [a for a in alerts if a["transaction_public_id"] == tx_id]
    assert matching == []
    tx = db_session.execute(select(Transaction).where(Transaction.transaction_id == tx_id)).scalar_one()
    db_session.expire_all()
    record = db_session.execute(
        select(RiskEvaluation).where(RiskEvaluation.transaction_id == tx.id)
    ).scalars().one()
    assert any(signal["rule_id"] == "ML" for signal in record.signals)
    assert record.hold_placed is False
