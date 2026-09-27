"""Individual rules R01–R12. Each returns a signal dict or None."""

from collections import defaultdict
from datetime import timedelta

from app.core.config import settings
from app.models.transaction import Transaction
from app.models.user import User
from app.services.risk.baselines import (
    AccountActivity,
    median_or_none,
    robust_z,
    threshold_from_baseline,
)
from app.services.risk.rules import RULES


def _signal(
    rule_id: str,
    subject: User,
    role: str,
    explanation: str,
    evidence: dict,
    modifier: int = 0,
    hold_basis: float = 0.0,
) -> dict:
    spec = RULES[rule_id]
    return {
        "rule_id": spec.id,
        "rule_name": spec.name,
        "version": spec.version,
        "family": spec.family,
        "severity": spec.severity,
        "base_weight": spec.base_weight,
        "modifier": modifier,
        "subject_user_id": subject.id,
        "subject_role": role,
        "explanation": explanation,
        "evidence": evidence,
        "hold_basis": hold_basis,
        "triggered": True,
    }


def _amount_similarity(amounts: list[float]) -> float:
    if len(amounts) < 2:
        return 1.0
    low, high = min(amounts), max(amounts)
    if high == 0:
        return 1.0
    return 1 - ((high - low) / high)


def rapid_same_pair(sender: AccountActivity, transaction: Transaction) -> dict | None:
    since = transaction.created_at - timedelta(seconds=settings.R01_WINDOW_SECONDS)
    count = sum(
        1
        for tx in sender.outbound(since)
        if tx.receiver_id == transaction.receiver_id
    )
    if count < settings.R01_MIN_COUNT:
        return None
    return _signal(
        "R01",
        sender.user,
        "sender",
        (
            f"{count} transfers from this account to the same recipient within "
            f"{settings.R01_WINDOW_SECONDS} seconds."
        ),
        {"count": count, "window_seconds": settings.R01_WINDOW_SECONDS},
    )


def account_velocity(activity: AccountActivity, role: str) -> dict | None:
    since = activity.now - timedelta(minutes=settings.R02_WINDOW_MINUTES)
    count = len(activity.outbound(since)) + len(activity.inbound(since))
    older = [
        tx
        for tx in activity.transactions
        if tx.created_at < since
    ]
    rate = None
    if not activity.thin_history and older:
        span_minutes = max(
            (since - min(tx.created_at for tx in older)).total_seconds() / 60,
            settings.R02_WINDOW_MINUTES,
        )
        rate = len(older) / (span_minutes / settings.R02_WINDOW_MINUTES)
    threshold = threshold_from_baseline(
        rate, settings.R02_FALLBACK_COUNT, settings.R02_BASELINE_MULTIPLIER
    )
    if count < threshold:
        return None
    return _signal(
        "R02",
        activity.user,
        role,
        (
            f"{count} transactions in {settings.R02_WINDOW_MINUTES} minutes, "
            f"above the threshold of {threshold}."
        ),
        {"count": count, "threshold": threshold, "window_minutes": settings.R02_WINDOW_MINUTES},
    )


def fan_in(receiver: AccountActivity) -> dict | None:
    since = receiver.now - timedelta(minutes=settings.R03_WINDOW_MINUTES)
    inbound = receiver.inbound(since)
    senders = {tx.sender_id for tx in inbound}
    if not senders:
        return None
    older = receiver.history_before(since)
    older_inbound = [tx for tx in older if tx.receiver_id == receiver.user.id]
    rate = None
    if not receiver.thin_history and older_inbound:
        span = max(
            (since - min(tx.created_at for tx in older_inbound)).total_seconds() / 60,
            settings.R03_WINDOW_MINUTES,
        )
        distinct_rate = len({tx.sender_id for tx in older_inbound}) / (
            span / settings.R03_WINDOW_MINUTES
        )
        rate = distinct_rate
    threshold = threshold_from_baseline(
        rate, settings.R03_FALLBACK_SENDERS, settings.R02_BASELINE_MULTIPLIER
    )
    if len(senders) < threshold:
        return None

    amounts = [float(tx.amount) for tx in inbound]
    similarity = _amount_similarity(amounts)
    prior_partners = {
        tx.sender_id
        for tx in receiver.history_before(since)
        if tx.receiver_id == receiver.user.id or tx.sender_id == receiver.user.id
    }
    new_senders = [sid for sid in senders if sid not in prior_partners]
    new_share = len(new_senders) / len(senders)
    modifier = 0
    if similarity >= settings.R03_AMOUNT_SIMILARITY:
        modifier += 3
    if new_share >= settings.R03_NEW_SENDER_SHARE:
        modifier += 5
    return _signal(
        "R03",
        receiver.user,
        "receiver",
        (
            f"{len(senders)} distinct accounts sent funds to this recipient within "
            f"{settings.R03_WINDOW_MINUTES} minutes."
        ),
        {
            "sender_count": len(senders),
            "window_minutes": settings.R03_WINDOW_MINUTES,
            "amount_similarity": round(similarity, 4),
            "new_counterparties": len(new_senders),
            "new_sender_share": round(new_share, 4),
            "sender_ids": sorted(senders),
        },
        modifier=modifier,
        hold_basis=sum(amounts),
    )


def fan_out(sender: AccountActivity) -> dict | None:
    since = sender.now - timedelta(minutes=settings.R04_WINDOW_MINUTES)
    outbound = sender.outbound(since)
    recipients = {tx.receiver_id for tx in outbound}
    older = [tx for tx in sender.history_before(since) if tx.sender_id == sender.user.id]
    rate = None
    if not sender.thin_history and older:
        span = max(
            (since - min(tx.created_at for tx in older)).total_seconds() / 60,
            settings.R04_WINDOW_MINUTES,
        )
        rate = len({tx.receiver_id for tx in older}) / (span / settings.R04_WINDOW_MINUTES)
    threshold = threshold_from_baseline(
        rate, settings.R04_FALLBACK_RECIPIENTS, settings.R02_BASELINE_MULTIPLIER
    )
    if len(recipients) < threshold:
        return None
    return _signal(
        "R04",
        sender.user,
        "sender",
        (
            f"Funds were sent to {len(recipients)} different recipients within "
            f"{settings.R04_WINDOW_MINUTES} minutes."
        ),
        {"recipient_count": len(recipients), "window_minutes": settings.R04_WINDOW_MINUTES},
    )


def unusually_large(sender: AccountActivity, transaction: Transaction) -> dict | None:
    history = [
        amount
        for amount in sender.prior_outbound_amounts()
        if True
    ]
    # Exclude the current transaction if it is already in the loaded window.
    history = [
        float(tx.amount)
        for tx in sender.transactions
        if tx.sender_id == sender.user.id and tx.id != transaction.id
    ]
    z = robust_z(float(transaction.amount), history)
    if z is None or z < settings.R05_ROBUST_Z:
        return None
    med = float(median_or_none(history) or 0)
    if float(transaction.amount) < settings.R05_MEDIAN_MULTIPLIER * med:
        return None
    return _signal(
        "R05",
        sender.user,
        "sender",
        (
            f"Amount {transaction.amount} ST is far above this account's median "
            f"transfer of {med:.2f} ST ({len(history)} past transfers)."
        ),
        {
            "amount": float(transaction.amount),
            "median": round(med, 2),
            "robust_z": round(z, 2),
            "history_count": len(history),
        },
    )


def structured_small(sender: AccountActivity) -> dict | None:
    since = sender.now - timedelta(minutes=settings.R06_WINDOW_MINUTES)
    small = [
        tx
        for tx in sender.outbound(since)
        if float(tx.amount) <= settings.R06_MAX_AMOUNT
    ]
    if len(small) < settings.R06_MIN_COUNT:
        return None
    aggregate = sum(float(tx.amount) for tx in small)
    older = [
        tx
        for tx in sender.transactions
        if tx.sender_id == sender.user.id and tx.created_at < since
    ]
    if not older:
        return None
    by_day: dict = defaultdict(float)
    for tx in older:
        by_day[tx.created_at.date()] += float(tx.amount)
    daily = median_or_none(list(by_day.values())) or 0
    if daily <= 0 or aggregate < settings.R06_DAILY_MULTIPLIER * daily:
        return None
    return _signal(
        "R06",
        sender.user,
        "sender",
        (
            f"{len(small)} small transfers totaling {aggregate:.2f} ST within "
            f"{settings.R06_WINDOW_MINUTES} minutes, above the usual daily outflow."
        ),
        {"count": len(small), "aggregate": round(aggregate, 2), "median_daily": round(daily, 2)},
    )


def dormant_reactivation(activity: AccountActivity, role: str) -> dict | None:
    since = activity.now - timedelta(hours=24)
    recent = activity.outbound(since) + activity.inbound(since)
    prior = activity.history_before(since)
    if not prior or len(recent) < 1:
        return None
    gap_days = (since - max(tx.created_at for tx in prior)).total_seconds() / 86400
    if gap_days < settings.R07_DORMANT_DAYS:
        return None
    prior_amounts = [float(tx.amount) for tx in prior if tx.sender_id == activity.user.id]
    med = median_or_none(prior_amounts) or 0
    aggregate = sum(float(tx.amount) for tx in recent if tx.sender_id == activity.user.id)
    if len(recent) < settings.R07_MIN_COUNT and not (
        med > 0 and aggregate >= settings.R07_MEDIAN_MULTIPLIER * med
    ):
        return None
    if len(recent) < settings.R07_MIN_COUNT and aggregate < settings.R07_MEDIAN_MULTIPLIER * max(med, 0.01):
        return None
    return _signal(
        "R07",
        activity.user,
        role,
        (
            f"No activity for {int(gap_days)} days, then {len(recent)} transfers "
            f"within 24 hours."
        ),
        {"gap_days": int(gap_days), "recent_count": len(recent), "aggregate": round(aggregate, 2)},
    )


def rapid_pass_through(activity: AccountActivity, role: str) -> dict | None:
    since = activity.now - timedelta(minutes=settings.R08_WINDOW_MINUTES)
    inbound = activity.inbound(since)
    outbound = activity.outbound(since)
    inflow = sum(float(tx.amount) for tx in inbound)
    outflow = sum(float(tx.amount) for tx in outbound)
    if inflow <= 0 or not outbound:
        return None
    ratio = outflow / inflow
    retained = max(inflow - outflow, 0) / inflow
    if ratio < settings.R08_FORWARD_RATIO or retained >= settings.R08_RETAINED_RATIO:
        return None
    return _signal(
        "R08",
        activity.user,
        role,
        (
            f"{ratio:.0%} of funds received in the last {settings.R08_WINDOW_MINUTES} minutes "
            f"was sent onward."
        ),
        {
            "inflow": round(inflow, 2),
            "outflow": round(outflow, 2),
            "forward_ratio": round(ratio, 4),
            "retained_ratio": round(retained, 4),
        },
        hold_basis=inflow,
    )


def circular_flow(sender: User, recent: list[Transaction], now) -> dict | None:
    window_start = now - timedelta(minutes=settings.R09_WINDOW_MINUTES)
    graph: dict[int, set[int]] = {}
    for tx in recent:
        if tx.created_at < window_start:
            continue
        graph.setdefault(tx.sender_id, set()).add(tx.receiver_id)
    origin = sender.id
    visited = {origin}

    def dfs(node: int, depth: int) -> int | None:
        if depth > settings.R09_MAX_HOPS:
            return None
        for neighbor in graph.get(node, set()):
            if neighbor == origin and depth >= 2:
                return depth
            if neighbor in visited:
                continue
            visited.add(neighbor)
            hops = dfs(neighbor, depth + 1)
            if hops is not None:
                return hops
        return None

    hops = dfs(origin, 1)
    if hops is None:
        return None
    return _signal(
        "R09",
        sender,
        "sender",
        (
            f"Funds circulated back to this account through {hops} hop(s) within "
            f"{settings.R09_WINDOW_MINUTES} minutes."
        ),
        {"hops": hops, "window_minutes": settings.R09_WINDOW_MINUTES},
    )


def mule_chain(recent: list[Transaction], now, focus: User) -> dict | None:
    """Walk backward from focus: each hop forwarded most of what it received."""
    window_start = now - timedelta(minutes=settings.R10_WINDOW_MINUTES)
    txs = [tx for tx in recent if tx.created_at >= window_start]
    inbound_by_user: dict[int, list[Transaction]] = defaultdict(list)
    outbound_by_user: dict[int, list[Transaction]] = defaultdict(list)
    for tx in txs:
        inbound_by_user[tx.receiver_id].append(tx)
        outbound_by_user[tx.sender_id].append(tx)

    def forwarded(user_id: int, outbound_amount: float) -> Transaction | None:
        credits = inbound_by_user.get(user_id, [])
        if not credits:
            return None
        inflow = sum(float(tx.amount) for tx in credits)
        if inflow <= 0 or outbound_amount / inflow < settings.R10_FORWARD_RATIO:
            return None
        return max(credits, key=lambda tx: tx.created_at)

    # Start from the latest outbound by focus, if any.
    outs = outbound_by_user.get(focus.id, [])
    if not outs:
        return None
    current_out = max(outs, key=lambda tx: tx.created_at)
    path = [focus.id, current_out.receiver_id]
    amount = float(current_out.amount)
    walker = focus.id
    hops = 0
    while hops < 6:
        credit = forwarded(walker, amount)
        if credit is None:
            break
        path.insert(0, credit.sender_id)
        amount = float(credit.amount)
        walker = credit.sender_id
        hops += 1
    # path includes focus and onward recipient; hops is pass-through steps before focus.
    # Total forwarding hops = hops (into focus) + 1 (focus onward) if focus forwarded.
    total_hops = hops + 1
    if total_hops < settings.R10_MIN_HOPS:
        return None
    return _signal(
        "R10",
        focus,
        "sender",
        (
            f"Funds passed through {len(path)} accounts within "
            f"{settings.R10_WINDOW_MINUTES} minutes, each keeping little."
        ),
        {
            "path_user_ids": path,
            "hops": total_hops,
            "window_minutes": settings.R10_WINDOW_MINUTES,
        },
        hold_basis=float(current_out.amount),
    )


def new_counterparty_burst(activity: AccountActivity, role: str) -> dict | None:
    since = activity.now - timedelta(minutes=settings.R11_WINDOW_MINUTES)
    recent = activity.outbound(since) + activity.inbound(since)
    prior_partners = set()
    for tx in activity.history_before(since):
        if tx.sender_id == activity.user.id:
            prior_partners.add(tx.receiver_id)
        elif tx.receiver_id == activity.user.id:
            prior_partners.add(tx.sender_id)
    fresh = set()
    for tx in recent:
        other = tx.receiver_id if tx.sender_id == activity.user.id else tx.sender_id
        if other not in prior_partners and other != activity.user.id:
            fresh.add(other)
    older_fresh_rate = None
    if not activity.thin_history:
        older_fresh_rate = 0.0
    threshold = threshold_from_baseline(
        older_fresh_rate if not activity.thin_history else None,
        settings.R11_FALLBACK_COUNT,
        settings.R02_BASELINE_MULTIPLIER,
    )
    if len(fresh) < threshold:
        return None
    return _signal(
        "R11",
        activity.user,
        role,
        f"{len(fresh)} counterparties in {settings.R11_WINDOW_MINUTES} minutes had no prior history with this account.",
        {"new_counterparties": len(fresh), "window_minutes": settings.R11_WINDOW_MINUTES},
    )


def concentration_change(sender: AccountActivity) -> dict | None:
    since = sender.now - timedelta(hours=settings.R12_WINDOW_HOURS)
    recent = sender.outbound(since)
    if len(recent) < settings.R12_MIN_COUNT:
        return None
    counts: dict[int, int] = defaultdict(int)
    for tx in recent:
        counts[tx.receiver_id] += 1
    top_id, top_count = max(counts.items(), key=lambda item: item[1])
    share = top_count / len(recent)
    if share < settings.R12_CONCENTRATION:
        return None
    usual = {
        tx.receiver_id
        for tx in sender.history_before(since)
        if tx.sender_id == sender.user.id
    }
    if sender.thin_history or top_id in usual:
        return None
    return _signal(
        "R12",
        sender.user,
        "sender",
        "Recent transfers concentrated on one recipient outside the usual set.",
        {"share": round(share, 4), "recipient_id": top_id, "count": len(recent)},
    )
