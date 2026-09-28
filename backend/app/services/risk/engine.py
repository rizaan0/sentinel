"""Run rules, context checks, scoring, and the explanation for one transfer."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from itertools import combinations

from app.models.case_event import CaseEvent
from app.models.enums import AlertStatus
from app.models.fraud_alert import FraudAlert
from app.models.transaction import Transaction
from app.models.user import User
from app.services import ml_anomaly_service
from app.services.risk.baselines import AccountActivity, load_activity, load_window
from app.services.risk.decision import (
    ACTION_ALLOW,
    ACTION_HOLD,
    ACTION_MONITOR,
    ACTION_STEP_UP,
    apply_family_dedup,
    match_pattern,
    score,
    select_action,
    should_hold,
    tier_for,
)
from app.services.risk.explain import narrate
from app.services.risk.rules import RULES_VERSION
from app.services.risk import signals as rule_signals


def _check(name: str, value, threshold, cleared: bool) -> dict:
    return {"check": name, "value": value, "threshold": threshold, "cleared": cleared}


def _context_checks(
    db: Session,
    focus: AccountActivity,
    inbound_senders: list[User],
    fired_ids: set[str],
    signature: dict | None = None,
) -> list[dict]:
    since = focus.now - timedelta(minutes=settings.R08_WINDOW_MINUTES)
    inbound = focus.inbound(since)
    outbound = focus.outbound(since)
    inflow = sum(float(tx.amount) for tx in inbound)
    outflow = sum(float(tx.amount) for tx in outbound)
    ratio = (outflow / inflow) if inflow else 0.0
    onward_cleared = ratio < 0.5

    since_fan = focus.now - timedelta(minutes=max(settings.R03_WINDOW_MINUTES, settings.R11_WINDOW_MINUTES))
    partners = set()
    for tx in focus.history_before(since_fan):
        if tx.sender_id == focus.user.id:
            partners.add(tx.receiver_id)
        elif tx.receiver_id == focus.user.id:
            partners.add(tx.sender_id)
    window_others = set()
    for tx in focus.inbound(since_fan) + focus.outbound(since_fan):
        other = tx.sender_id if tx.receiver_id == focus.user.id else tx.receiver_id
        if other != focus.user.id:
            window_others.add(other)
    known_share = (
        len(window_others & partners) / len(window_others) if window_others else 1.0
    )

    day_start = focus.now - timedelta(hours=24)
    today_count = len(focus.inbound(day_start)) + len(focus.outbound(day_start))
    activity_cleared = focus.thin_history or today_count <= max(settings.R02_FALLBACK_COUNT, 10)

    young_cutoff = focus.now - timedelta(days=settings.NEW_ACCOUNT_DAYS)
    sender_ids = [user.id for user in inbound_senders]
    risky_alerts = []
    if sender_ids:
        risky_alerts = (
            db.execute(
                select(FraudAlert.id).where(
                    FraudAlert.user_id.in_(sender_ids),
                    FraudAlert.status.in_(
                        [AlertStatus.OPEN, AlertStatus.INVESTIGATING, AlertStatus.CONFIRMED_FRAUD]
                    ),
                )
            )
            .scalars()
            .all()
        )
    young = [user for user in inbound_senders if user.created_at >= young_cutoff]
    sender_cleared = not young and not risky_alerts

    age_days = (focus.now - focus.user.created_at).total_seconds() / 86400
    confirmed = (
        db.execute(
            select(FraudAlert.id).where(
                FraudAlert.user_id == focus.user.id,
                FraudAlert.status == AlertStatus.CONFIRMED_FRAUD,
            )
        )
        .scalars()
        .first()
    )
    inbound_cleared = focus.thin_history or "R03" not in fired_ids
    reviewed = _reviewed_pattern(db, focus, signature)

    return [
        _check("onward_transfer_ratio", round(ratio, 4), 0.5, onward_cleared),
        _check("known_counterparties", round(known_share, 4), 0.5, known_share >= 0.5),
        _check("inbound_profile", today_count, None, inbound_cleared),
        _check("sender_risk", len(young) + len(list(risky_alerts)), 0, sender_cleared),
        _check("activity_abnormality", today_count, settings.R02_FALLBACK_COUNT, activity_cleared),
        _check("account_maturity", round(age_days, 1), settings.MATURE_ACCOUNT_DAYS, age_days >= settings.MATURE_ACCOUNT_DAYS and not confirmed),
        {
            "check": "reviewed_legitimate_pattern",
            "value": reviewed["matched"],
            "threshold": True,
            "cleared": reviewed["matched"],
            "detail": reviewed["detail"],
        },
    ]


def _ml_signal(db: Session, transaction: Transaction, subject: User) -> dict | None:
    result = ml_anomaly_service.evaluate(db, transaction)
    if result is None:
        return None
    return {
        "rule_id": "ML",
        "rule_name": "ML Anomaly",
        "version": 1,
        "family": "model",
        "severity": "soft",
        "base_weight": min(settings.ML_SIGNAL_CAP, 15),
        "modifier": 0,
        "subject_user_id": subject.id,
        "subject_role": "sender",
        "explanation": (
            "ML Anomaly Detector flagged this transaction as unusual for this account "
            f"(anomaly score {result['anomaly_score']:.3f})."
        ),
        "evidence": {"anomaly_score": result["anomaly_score"]},
        "hold_basis": 0.0,
        "triggered": True,
    }


def evaluate(db: Session, transaction: Transaction) -> dict | None:
    sender = transaction.sender
    receiver = transaction.receiver
    now = transaction.created_at
    sender_activity = load_activity(db, sender, now)
    receiver_activity = load_activity(db, receiver, now)
    recent = load_window(db, now - timedelta(minutes=settings.R10_WINDOW_MINUTES), now)

    raw: list[dict] = []
    for candidate in (
        rule_signals.rapid_same_pair(sender_activity, transaction),
        rule_signals.account_velocity(sender_activity, "sender"),
        rule_signals.account_velocity(receiver_activity, "receiver"),
        rule_signals.fan_in(receiver_activity),
        rule_signals.fan_in(sender_activity),
        rule_signals.fan_out(sender_activity),
        rule_signals.unusually_large(sender_activity, transaction),
        rule_signals.structured_small(sender_activity),
        rule_signals.dormant_reactivation(sender_activity, "sender"),
        rule_signals.dormant_reactivation(receiver_activity, "receiver"),
        rule_signals.rapid_pass_through(sender_activity, "sender"),
        rule_signals.rapid_pass_through(receiver_activity, "receiver"),
        rule_signals.circular_flow(sender, recent, now),
        rule_signals.mule_chain(recent, now, sender),
        rule_signals.new_counterparty_burst(sender_activity, "sender"),
        rule_signals.new_counterparty_burst(receiver_activity, "receiver"),
        rule_signals.concentration_change(sender_activity),
        _ml_signal(db, transaction, sender),
    ):
        if candidate is not None:
            raw.append(candidate)

    if not raw:
        return None

    # One signal per rule id; keep the copy with the larger weight.
    merged: dict[str, dict] = {}
    for signal in raw:
        key = signal["rule_id"]
        weight = signal["base_weight"] + signal.get("modifier", 0)
        current = merged.get(key)
        if current is None or weight > current["base_weight"] + current.get("modifier", 0):
            merged[key] = signal
    raw = list(merged.values())

    scored = apply_family_dedup(raw)
    focus_id = max(
        scored,
        key=lambda signal: signal["score_contribution"] + signal["base_weight"],
    )["subject_user_id"]
    focus_activity = sender_activity if focus_id == sender.id else receiver_activity
    inbound_ids = {
        tx.sender_id
        for tx in focus_activity.inbound(now - timedelta(minutes=settings.R03_WINDOW_MINUTES))
    }
    inbound_users = []
    if inbound_ids:
        inbound_users = list(
            db.execute(select(User).where(User.id.in_(inbound_ids))).scalars().all()
        )
    signature = _pattern_signature(scored, focus_activity)
    checks = _context_checks(
        db, focus_activity, inbound_users, {s["rule_id"] for s in scored}, signature
    )
    pattern = match_pattern(scored, checks)
    breakdown = score(scored, checks, pattern)
    tier = tier_for(breakdown["final"], scored, pattern)
    hold = should_hold(tier, pattern, scored)
    hold_amount = 0.0
    if hold:
        bases = [signal.get("hold_basis") or 0 for signal in scored if signal["score_contribution"] > 0]
        hold_amount = max(bases) if any(bases) else float(transaction.amount)
    action = select_action(tier, pattern, scored)
    trace = _decision_trace(raw, scored, checks, breakdown["final"], action)
    trace["signature"] = signature
    narrative = narrate(breakdown["final"], scored, checks, pattern, tier, hold)
    subject_role = "receiver" if focus_id == receiver.id else "sender"
    return {
        "subject_user_id": focus_id,
        "subject_role": subject_role,
        "tier": tier,
        "pattern": pattern,
        "signals": scored,
        "context_checks": checks,
        "score_breakdown": breakdown,
        "risk_score": breakdown["final"],
        "rules_version": RULES_VERSION,
        "narrative": narrative,
        "hold": hold,
        "hold_amount": hold_amount,
        "action": action,
        "decision_trace": trace,
        "signature": signature,
    }


def _pattern_signature(signals: list[dict], focus: AccountActivity) -> dict:
    fan_in = next((signal for signal in signals if signal["rule_id"] == "R03"), None)
    sender_ids = []
    if fan_in is not None:
        sender_ids = list((fan_in.get("evidence") or {}).get("sender_ids") or [])
    outbound = focus.outbound(focus.now - timedelta(minutes=settings.R08_WINDOW_MINUTES))
    onward = outbound[-1].receiver_id if outbound else None
    families = sorted({signal["family"] for signal in signals})
    return {
        "subject_user_id": focus.user.id,
        "sender_ids": sender_ids,
        "onward_recipient_id": onward,
        "families": families,
    }


def _signatures_match(stored: dict, current: dict) -> bool:
    stored_senders = set(stored.get("sender_ids") or [])
    current_senders = set(current.get("sender_ids") or [])
    if stored_senders or current_senders:
        if not stored_senders or not current_senders:
            return False
        if len(stored_senders & current_senders) / len(stored_senders) < 0.6:
            return False
    if stored.get("onward_recipient_id") != current.get("onward_recipient_id"):
        return False
    return set(stored.get("families") or []) == set(current.get("families") or [])


def _reviewed_pattern(db: Session, focus: AccountActivity, signature: dict | None) -> dict:
    if (
        db.execute(
            select(FraudAlert.id).where(
                FraudAlert.user_id == focus.user.id,
                FraudAlert.status == AlertStatus.CONFIRMED_FRAUD,
            )
        )
        .scalars()
        .first()
    ):
        return {"matched": False, "detail": None}
    since = focus.now - timedelta(days=settings.FALSE_POSITIVE_LOOKBACK_DAYS)
    events = (
        db.execute(
            select(CaseEvent).where(
                CaseEvent.kind == "review",
                CaseEvent.created_at >= since,
            )
        )
        .scalars()
        .all()
    )
    current = signature or {}
    for event in events:
        detail = event.detail or {}
        if detail.get("subject_user_id") != focus.user.id:
            continue
        if not _signatures_match(detail, current):
            continue
        when = event.created_at.date().isoformat()
        reason = str(detail.get("reason", "other")).replace("_", " ")
        return {
            "matched": True,
            "detail": f"This pattern was reviewed as legitimate on {when}: {reason}.",
        }
    return {"matched": False, "detail": None}


def _context_lines(signals: list[dict]) -> list[str]:
    lines = []
    for signal in signals:
        if signal.get("score_contribution", 0) <= 0:
            continue
        evidence = signal.get("evidence") or {}
        rule_id = signal["rule_id"]
        if rule_id == "R03":
            lines.append(
                f"{evidence.get('sender_count', 'Several')} senders in {evidence.get('window_minutes', 2)} minutes"
            )
        elif rule_id == "R08":
            ratio = evidence.get("forward_ratio")
            percent = int(float(ratio) * 100) if ratio is not None else 90
            lines.append(f"{percent}% forwarded within {evidence.get('window_minutes', 30)} minutes")
        elif rule_id == "R11":
            lines.append(
                "Recipient had no prior history"
                if evidence.get("new_counterparties")
                else signal["rule_name"]
            )
        else:
            lines.append(signal["rule_name"])
    return lines


def _action_phrase(action: str) -> str:
    if action == ACTION_ALLOW:
        return "the transfer is allowed"
    if action == ACTION_MONITOR:
        return "the transfer is allowed with monitoring"
    if action == ACTION_STEP_UP:
        return "the transfer asks for confirmation"
    if action == ACTION_HOLD:
        return "the transfer is held"
    return action


def _rescore(raw: list[dict], checks: list[dict], drop: set[str]) -> tuple[int, str]:
    kept = [signal for signal in raw if signal["rule_id"] not in drop]
    if not kept:
        return 0, ACTION_ALLOW
    scored = apply_family_dedup(kept)
    pattern = match_pattern(scored, checks)
    final = score(scored, checks, pattern)["final"]
    tier = tier_for(final, scored, pattern)
    return final, select_action(tier, pattern, scored)


def _decision_trace(raw: list[dict], scored: list[dict], checks: list[dict], final: int, action: str) -> dict:
    contributing = [signal for signal in scored if signal.get("score_contribution", 0) > 0]
    counterfactuals = []
    smallest = None
    ids = [signal["rule_id"] for signal in contributing]
    for size in range(1, len(ids) + 1):
        for combo in combinations(ids, size):
            new_score, new_action = _rescore(raw, checks, set(combo))
            names = ", ".join(
                signal["rule_name"] for signal in contributing if signal["rule_id"] in combo
            )
            line = (
                f"Without {names}, the score falls from {final} to {new_score} and {_action_phrase(new_action)}."
            )
            if size == 1:
                counterfactuals.append(
                    {"removed": list(combo), "score": new_score, "action": new_action, "text": line}
                )
            if new_action == ACTION_ALLOW and smallest is None:
                smallest = {"removed": list(combo), "score": new_score, "action": new_action, "text": line}
        if smallest is not None:
            break
    return {
        "action": action,
        "rules": [
            {"rule_id": signal["rule_id"], "rule_name": signal["rule_name"], "points": signal["score_contribution"]}
            for signal in contributing
        ],
        "context": _context_lines(scored),
        "counterfactuals": counterfactuals,
        "smallest_allow": smallest,
    }
