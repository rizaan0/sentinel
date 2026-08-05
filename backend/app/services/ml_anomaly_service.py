"""
ML Anomaly Detector: loads the trained Isolation Forest artifact (see
ml/train_model.py) and scores a transaction. This is one of the Monitoring
Engine's parallel evaluators alongside the Rule Engine and Statistics. If
no model has been trained yet, this degrades gracefully - the platform
still functions on rules alone (a solid foundation before advanced
functionality).
"""
import logging
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.services.ml_features import extract_features

logger = logging.getLogger("sentinel.ml_anomaly")

ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "ml_artifacts" / "anomaly_model.joblib"

_cached_artifact: dict | None = None
_load_attempted = False


def _load_artifact() -> dict | None:
    global _cached_artifact, _load_attempted
    if _load_attempted:
        return _cached_artifact
    _load_attempted = True
    if ARTIFACT_PATH.exists():
        try:
            _cached_artifact = joblib.load(ARTIFACT_PATH)
            logger.info("Loaded ML anomaly model from %s", ARTIFACT_PATH)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load ML anomaly model from %s", ARTIFACT_PATH)
    else:
        logger.info("No ML anomaly model found at %s; ML scoring disabled", ARTIFACT_PATH)
    return _cached_artifact


def reset_cache() -> None:
    """Forces a fresh artifact load on next call - used by tests and after retraining."""
    global _cached_artifact, _load_attempted
    _cached_artifact, _load_attempted = None, False


def evaluate(db: Session, transaction: Transaction) -> dict | None:
    """Returns a result dict if the transaction is flagged as anomalous, else None."""
    artifact = _load_artifact()
    if artifact is None:
        return None

    model = artifact["model"]
    feature_columns = artifact["feature_columns"]
    feature_vector = extract_features(db, transaction)
    x = pd.DataFrame([feature_vector], columns=feature_columns)

    prediction = model.predict(x)[0]  # -1 = anomaly, 1 = normal
    if prediction != -1:
        return None

    score = model.decision_function(x)[0]  # lower = more anomalous
    return {"is_anomaly": True, "anomaly_score": float(score)}
