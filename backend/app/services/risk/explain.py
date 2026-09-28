"""Deterministic narrative. Works when the language model is offline."""

PATTERN_NAMES = {
    "A": "Legitimate-looking group payment",
    "B": "Possible mule",
    "C": "Possible automated abuse",
    "D": "Structuring",
    "E": "Mule network",
    "F": "Dormant takeover or mule",
}

TIER_DECISIONS = {
    "normal": "Unusual pattern recorded. Not enough evidence to restrict the account.",
    "low_anomaly": "Suspicious pattern recorded. Not enough evidence to restrict the account.",
    "suspicious": "Suspicious. Allowed, and opened for investigation.",
    "high": "High risk. Investigation required.",
    "critical": "Critical risk. The flagged amount is on hold pending investigation.",
}


def _check_phrase(check: dict) -> str:
    name = check["check"].replace("_", " ")
    state = "cleared" if check.get("cleared") else "did not clear"
    return f"{name} {state}"


def narrate(
    score: int,
    signals: list[dict],
    checks: list[dict],
    pattern: str | None,
    tier: str,
    held: bool,
) -> str:
    parts = [f"Risk score: {score}/100."]
    contributing = [signal for signal in signals if signal.get("score_contribution", 0) > 0]
    evidence_only = [signal for signal in signals if signal.get("score_contribution", 0) == 0]
    if contributing:
        parts.append("Triggered rules:")
        for signal in contributing:
            parts.append(
                f"{signal['rule_id']} — {signal['rule_name']} (+{signal['score_contribution']}): "
                f"{signal['explanation']}"
            )
    if evidence_only:
        parts.append(
            "Related rules noted without extra score, because a stronger rule in the same family already counted: "
            + ", ".join(signal["rule_id"] for signal in evidence_only)
            + "."
        )
    cleared = [check for check in checks if check.get("cleared")]
    failed = [check for check in checks if not check.get("cleared")]
    reviewed = next(
        (check for check in checks if check["check"] == "reviewed_legitimate_pattern" and check.get("detail")),
        None,
    )
    if reviewed:
        parts.append(reviewed["detail"])
    if cleared:
        parts.append("Context that lowered concern: " + "; ".join(_check_phrase(c) for c in cleared) + ".")
    if failed:
        parts.append("Context that did not clear: " + "; ".join(_check_phrase(c) for c in failed) + ".")
    if pattern:
        parts.append(f"Pattern {pattern}: {PATTERN_NAMES.get(pattern, pattern)}.")
        if pattern == "A":
            parts.append(
                "The fan-in pattern alone is not treated as fraud, because legitimate group payments look the same."
            )
        elif pattern == "B":
            parts.append(
                "Risk rose because the incoming burst was combined with rapid onward transfer to new counterparties."
            )
    decision = TIER_DECISIONS.get(tier, tier)
    if held and tier != "critical":
        decision = "High risk. The flagged amount is on hold pending investigation."
    parts.append(f"Decision: {decision}")
    return " ".join(parts)
