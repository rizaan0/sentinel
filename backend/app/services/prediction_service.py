"""
Forward-looking risk forecast.

Each account gets a daily risk series from the last 7 days (stored monitoring
scores, or a behavior score when no rule fired). A straight-line fit of that
series is extended 7 days ahead. The result is a future risk score, not a
fraud verdict. Drivers are the measured changes between this week and the
week before. No confidence figure is invented.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import RiskLevel
from app.models.fraud_alert import FraudAlert
from app.models.risk_evaluation import RiskEvaluation
from app.models.risk_prediction import RiskPrediction
from app.models.transaction import Transaction

HISTORY_DAYS = 7
HORIZON_DAYS = 7
HIGH_THRESHOLD = 60
MEDIUM_THRESHOLD = 30


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment


def _level(score: int) -> RiskLevel:
    if score >= HIGH_THRESHOLD:
        return RiskLevel.HIGH
    if score >= MEDIUM_THRESHOLD:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _trend(change: int) -> str:
    if change >= 8:
        return "increasing"
    if change <= -8:
        return "decreasing"
    return "stable"


def _project(scores: list[int]) -> list[int]:
    """Least-squares line through the daily scores, extended HORIZON_DAYS ahead."""
    count = len(scores)
    if count == 0:
        return [0] * HORIZON_DAYS
    if count == 1:
        return [scores[0]] * HORIZON_DAYS
    xs = list(range(count))
    x_bar = sum(xs) / count
    y_bar = sum(scores) / count
    variance = sum((x - x_bar) ** 2 for x in xs)
    if variance == 0:
        slope = 0.0
        intercept = y_bar
    else:
        slope = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, scores)) / variance
        intercept = y_bar - slope * x_bar
    forecast = []
    for step in range(count, count + HORIZON_DAYS):
        value = round(intercept + slope * step)
        forecast.append(max(0, min(100, value)))
    return forecast


def _behavior_score(outbound: int, inbound: int, new_parties: int, fan_in: int, fan_out: int, large: bool, passthrough: bool) -> int:
    points = 0
    if outbound + inbound > 1:
        points += min(30, (outbound + inbound - 1) * 6)
    points += min(20, new_parties * 5)
    if fan_in >= 3:
        points += min(15, fan_in * 3)
    if fan_out >= 3:
        points += min(15, fan_out * 3)
    if large:
        points += 15
    if passthrough:
        points += 20
    return min(100, points)


def _window_stats(txs: list[Transaction], user_id: int, start: datetime, end: datetime, known: set[int]) -> dict:
    window = [tx for tx in txs if start <= _aware(tx.created_at) < end]
    outbound = [tx for tx in window if tx.sender_id == user_id]
    inbound = [tx for tx in window if tx.receiver_id == user_id]
    fresh = set()
    for tx in window:
        other = tx.receiver_id if tx.sender_id == user_id else tx.sender_id
        if other not in known and other != user_id:
            fresh.add(other)
    inflow = sum(float(tx.amount) for tx in inbound)
    outflow = sum(float(tx.amount) for tx in outbound)
    amounts = [float(tx.amount) for tx in outbound]
    return {
        "outbound": len(outbound),
        "inbound": len(inbound),
        "new_counterparties": len(fresh),
        "fan_in": len({tx.sender_id for tx in inbound}),
        "fan_out": len({tx.receiver_id for tx in outbound}),
        "passthrough": inflow > 0 and outflow / inflow >= 0.8,
        "avg_amount": (sum(amounts) / len(amounts)) if amounts else 0.0,
        "partners": {
            (tx.receiver_id if tx.sender_id == user_id else tx.sender_id)
            for tx in window
            if (tx.receiver_id if tx.sender_id == user_id else tx.sender_id) != user_id
        },
    }


def _drivers(recent: dict, prior: dict, recent_signals: int, prior_signals: int) -> list[str]:
    lines = []
    if prior["outbound"] > 0 and recent["outbound"] / prior["outbound"] >= 1.5:
        ratio = recent["outbound"] / prior["outbound"]
        lines.append(f"Transaction velocity increased {ratio:.1f}× over the last 7 days.")
    elif prior["outbound"] == 0 and recent["outbound"] >= 3:
        lines.append(f"Outbound transfers rose to {recent['outbound']} in the last 7 days.")
    if recent["new_counterparties"] > prior["new_counterparties"]:
        lines.append(
            "New counterparties increased from "
            f"{prior['new_counterparties']} to {recent['new_counterparties']}."
        )
    if recent_signals > prior_signals:
        lines.append(
            "Fraud signals appeared more frequently than the previous period "
            f"({recent_signals} versus {prior_signals})."
        )
    if recent["fan_in"] >= 5 and recent["fan_in"] > prior["fan_in"]:
        lines.append(
            f"Fan-in activity rose from {prior['fan_in']} to {recent['fan_in']} distinct senders."
        )
    if recent["fan_out"] >= 5 and recent["fan_out"] > prior["fan_out"]:
        lines.append(
            f"Fan-out activity rose from {prior['fan_out']} to {recent['fan_out']} distinct recipients."
        )
    if recent["passthrough"] and not prior["passthrough"]:
        lines.append("Funds received this week were sent onward quickly.")
    if prior["avg_amount"] > 0 and recent["avg_amount"] >= prior["avg_amount"] * 2:
        lines.append("Average outbound amount is at least twice the previous week.")
    return lines


def _explain(current: int, predicted: int, drivers: list[str]) -> str:
    if predicted > current:
        lead = (
            f"Predicted risk is expected to increase from {current} to {predicted} "
            "over the next 7 days."
        )
    elif predicted < current:
        lead = (
            f"Predicted risk is expected to decrease from {current} to {predicted} "
            "over the next 7 days."
        )
    else:
        lead = f"Predicted risk is expected to stay near {current} over the next 7 days."
    if drivers:
        return lead + " " + " ".join(drivers)
    if predicted != current:
        return lead + " Recent daily risk differs from earlier days in the week."
    return lead + " Recent activity does not show a material change from the previous week."


def compute_predictions(db: Session) -> list[RiskPrediction]:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    history_start = today - timedelta(days=HISTORY_DAYS - 1)
    prior_start = history_start - timedelta(days=HISTORY_DAYS)
    load_from = prior_start

    transactions = list(
        db.execute(
            select(Transaction).where(Transaction.created_at >= load_from, Transaction.created_at <= now)
        ).scalars().all()
    )
    evaluations = list(
        db.execute(
            select(RiskEvaluation).where(RiskEvaluation.created_at >= load_from, RiskEvaluation.created_at <= now)
        ).scalars().all()
    )
    alerts = list(
        db.execute(
            select(FraudAlert).where(FraudAlert.created_at >= load_from, FraudAlert.created_at <= now)
        ).scalars().all()
    )

    user_ids = set()
    txs_by_user: dict[int, list[Transaction]] = {}
    for tx in transactions:
        for user_id in (tx.sender_id, tx.receiver_id):
            user_ids.add(user_id)
            txs_by_user.setdefault(user_id, []).append(tx)
    evals_by_user: dict[int, list[RiskEvaluation]] = {}
    for row in evaluations:
        user_ids.add(row.subject_user_id)
        evals_by_user.setdefault(row.subject_user_id, []).append(row)
    alerts_by_user: dict[int, list[FraudAlert]] = {}
    for row in alerts:
        user_ids.add(row.user_id)
        alerts_by_user.setdefault(row.user_id, []).append(row)

    day_starts = [history_start + timedelta(days=offset) for offset in range(HISTORY_DAYS)]
    predictions: list[RiskPrediction] = []
    for user_id in user_ids:
        user_txs = txs_by_user.get(user_id, [])
        user_evals = evals_by_user.get(user_id, [])
        user_alerts = alerts_by_user.get(user_id, [])
        older_amounts = [
            float(tx.amount)
            for tx in user_txs
            if tx.sender_id == user_id and _aware(tx.created_at) < history_start
        ]
        median = sorted(older_amounts)[len(older_amounts) // 2] if older_amounts else 0.0
        known: set[int] = set()
        for tx in user_txs:
            if _aware(tx.created_at) < history_start:
                other = tx.receiver_id if tx.sender_id == user_id else tx.sender_id
                if other != user_id:
                    known.add(other)

        daily = []
        for start in day_starts:
            end = start + timedelta(days=1)
            stats = _window_stats(user_txs, user_id, start, end, known)
            large = median > 0 and stats["avg_amount"] >= median * 3
            behavior = _behavior_score(
                stats["outbound"],
                stats["inbound"],
                stats["new_counterparties"],
                stats["fan_in"],
                stats["fan_out"],
                large,
                stats["passthrough"],
            )
            stored = [
                row.risk_score
                for row in user_evals
                if start <= _aware(row.created_at) < end
            ] + [
                row.risk_score
                for row in user_alerts
                if start <= _aware(row.created_at) < end
            ]
            daily.append(max([behavior, *stored]) if stored else behavior)

        if max(daily) < 15:
            continue

        forecast = _project(daily)
        current = daily[-1]
        predicted = forecast[-1]
        change = predicted - current
        recent = _window_stats(user_txs, user_id, history_start, now + timedelta(seconds=1), known)
        prior_known: set[int] = set()
        prior = _window_stats(user_txs, user_id, prior_start, history_start, prior_known)
        recent_signals = sum(
            1 for row in user_evals if _aware(row.created_at) >= history_start
        ) + sum(1 for row in user_alerts if _aware(row.created_at) >= history_start)
        prior_signals = sum(
            1 for row in user_evals if prior_start <= _aware(row.created_at) < history_start
        ) + sum(1 for row in user_alerts if prior_start <= _aware(row.created_at) < history_start)
        drivers = _drivers(recent, prior, recent_signals, prior_signals)
        series = [
            {"offset": offset - (HISTORY_DAYS - 1), "score": score, "kind": "actual"}
            for offset, score in enumerate(daily)
        ] + [
            {"offset": step + 1, "score": score, "kind": "predicted"}
            for step, score in enumerate(forecast)
        ]
        predictions.append(
            RiskPrediction(
                user_id=user_id,
                predicted_risk_level=_level(predicted),
                trend_score=float(predicted),
                alerts_last_7d=recent_signals,
                alerts_prior_7d=prior_signals,
                avg_risk_score_last_7d=float(current),
                current_risk=current,
                predicted_7d_risk=predicted,
                risk_change=change,
                trend=_trend(change),
                horizon_days=HORIZON_DAYS,
                series=series,
                drivers=drivers,
                explanation=_explain(current, predicted, drivers),
            )
        )

    predictions.sort(key=lambda row: (row.risk_change, row.predicted_7d_risk), reverse=True)
    db.add_all(predictions)
    db.commit()
    for prediction in predictions:
        db.refresh(prediction)
    return predictions


def get_latest_predictions(db: Session) -> list[RiskPrediction]:
    """One row per user: their most recently computed forecast, rising risk first."""
    latest_per_user = (
        select(RiskPrediction.user_id, func.max(RiskPrediction.created_at).label("latest"))
        .group_by(RiskPrediction.user_id)
        .subquery()
    )
    return (
        db.execute(
            select(RiskPrediction)
            .join(
                latest_per_user,
                (RiskPrediction.user_id == latest_per_user.c.user_id)
                & (RiskPrediction.created_at == latest_per_user.c.latest),
            )
            .order_by(RiskPrediction.risk_change.desc(), RiskPrediction.predicted_7d_risk.desc())
        )
        .scalars()
        .all()
    )
