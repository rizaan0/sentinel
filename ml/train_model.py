"""
Offline training pipeline for the ML Anomaly Detector.

Loads completed transactions from the database (synthetic data generated
by synthetic_generator.py initially; later, real accumulated platform data
- this is the same, documented retraining path either way), computes
features, trains an unsupervised Isolation Forest (unsupervised because
idea.md's fraud emerges from behavior, never from hand-applied labels),
evaluates against the synthetic persona labels for reporting only, and
exports the artifact backend/app/services/ml_anomaly_service.py loads.

Usage (from backend/, so `app` resolves against the right DATABASE_URL):
    ..\\.venv\\Scripts\\python.exe ..\\ml\\train_model.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

import joblib
import pandas as pd
from app.db.base import Base  # noqa: F401  (registers all models with the ORM registry)
from app.db.session import SessionLocal
from app.models.enums import TransactionStatus
from app.models.transaction import Transaction
from feature_engineering import FEATURE_COLUMNS, build_feature_frame
from sklearn.ensemble import IsolationForest
from sqlalchemy import select

ARTIFACT_PATH = (
    Path(__file__).resolve().parents[1] / "backend" / "app" / "ml_artifacts" / "anomaly_model.joblib"
)
LABELS_PATH = Path(__file__).resolve().parent / "artifacts" / "persona_labels.csv"
CONTAMINATION = 0.08  # expected proportion of anomalous transactions


def load_transactions_dataframe() -> pd.DataFrame:
    db = SessionLocal()
    try:
        rows = (
            db.execute(select(Transaction).where(Transaction.status == TransactionStatus.COMPLETED))
            .scalars()
            .all()
        )
        return pd.DataFrame(
            [
                {
                    "transaction_id": t.transaction_id,
                    "sender_id": t.sender_id,
                    "receiver_id": t.receiver_id,
                    "amount": float(t.amount),
                    "created_at": pd.Timestamp(t.created_at),
                }
                for t in rows
            ]
        )
    finally:
        db.close()


def main() -> None:
    df = load_transactions_dataframe()
    if df.empty:
        print("No transactions found. Run synthetic_generator.py first.")
        return

    features = build_feature_frame(df)
    x = features[FEATURE_COLUMNS]

    model = IsolationForest(n_estimators=200, contamination=CONTAMINATION, random_state=42)
    model.fit(x)

    predictions = model.predict(x)  # -1 = anomaly, 1 = normal
    features["predicted_anomaly"] = predictions == -1

    if LABELS_PATH.exists():
        labels = pd.read_csv(LABELS_PATH)
        merged = features.merge(labels, on="transaction_id", how="left")
        merged["persona"] = merged["persona"].fillna("unknown")
        print("\nDetection rate by persona (share flagged anomalous):")
        print(merged.groupby("persona")["predicted_anomaly"].mean())

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": FEATURE_COLUMNS}, ARTIFACT_PATH)
    print(f"\nModel trained on {len(df)} transactions. Saved to {ARTIFACT_PATH}")


if __name__ == "__main__":
    main()
