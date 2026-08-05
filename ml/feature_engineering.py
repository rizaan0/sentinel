"""
Offline feature engineering for the ML Anomaly Detector.

This computes features over a full historical dataset (pandas, at training
time). The online counterpart, backend/app/services/ml_features.py,
computes the SAME named features per-transaction via SQL at inference
time. Keep both in sync if the feature set changes.

Features:
- amount: the transfer amount itself
- sender_avg_amount_30d / sender_std_amount_30d: sender's own transfer
  history baseline over the trailing 30 days (excluding this transaction)
- sender_txn_count_1h / sender_txn_count_24h: recent activity volume
- unique_receivers_24h: fan-out breadth in the last 24h
- amount_to_avg_ratio: how unusual this amount is relative to the sender's
  own baseline
- hour_of_day: time-of-day pattern
- is_new_receiver: whether the sender has never paid this receiver before
"""
import pandas as pd

FEATURE_COLUMNS = [
    "amount",
    "sender_avg_amount_30d",
    "sender_std_amount_30d",
    "sender_txn_count_1h",
    "sender_txn_count_24h",
    "unique_receivers_24h",
    "amount_to_avg_ratio",
    "hour_of_day",
    "is_new_receiver",
]


def build_feature_frame(transactions: pd.DataFrame) -> pd.DataFrame:
    """
    `transactions` must have columns: transaction_id, sender_id,
    receiver_id, amount (float), created_at (datetime64, tz-aware or naive
    but consistent). Returns a DataFrame with `transaction_id` plus
    FEATURE_COLUMNS, one row per input transaction.
    """
    df = transactions.sort_values("created_at").reset_index(drop=True)
    rows: list[dict] = []

    for _sender_id, group in df.groupby("sender_id"):
        group = group.sort_values("created_at")
        history_amounts: list[float] = []
        history_times: list[pd.Timestamp] = []
        history_receivers: list[int] = []

        for _, row in group.iterrows():
            now = row["created_at"]

            window_30d = [
                a for a, t in zip(history_amounts, history_times) if (now - t).total_seconds() <= 30 * 86400
            ]
            count_1h = sum(1 for t in history_times if (now - t).total_seconds() <= 3600)
            recent_24h = [
                (a, r)
                for a, t, r in zip(history_amounts, history_times, history_receivers)
                if (now - t).total_seconds() <= 86400
            ]
            count_24h = len(recent_24h)
            unique_receivers_24h = len({r for _, r in recent_24h})

            avg = (sum(window_30d) / len(window_30d)) if window_30d else 0.0
            if len(window_30d) > 1:
                variance = sum((a - avg) ** 2 for a in window_30d) / len(window_30d)
                std = variance**0.5
            else:
                std = 0.0

            is_new_receiver = row["receiver_id"] not in history_receivers
            ratio = (row["amount"] / (avg + 1e-6)) if avg > 0 else 1.0

            rows.append(
                {
                    "transaction_id": row["transaction_id"],
                    "amount": row["amount"],
                    "sender_avg_amount_30d": avg,
                    "sender_std_amount_30d": std,
                    "sender_txn_count_1h": count_1h,
                    "sender_txn_count_24h": count_24h,
                    "unique_receivers_24h": unique_receivers_24h,
                    "amount_to_avg_ratio": ratio,
                    "hour_of_day": now.hour,
                    "is_new_receiver": int(is_new_receiver),
                }
            )

            history_amounts.append(row["amount"])
            history_times.append(now)
            history_receivers.append(row["receiver_id"])

    result = pd.DataFrame(rows)
    # Re-align to the original input order/index.
    result = result.set_index("transaction_id").loc[df["transaction_id"]].reset_index()
    return result
