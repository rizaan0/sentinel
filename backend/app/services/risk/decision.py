"""Family de-duplication, context reductions, named patterns, and action tiers."""

from app.core.config import settings

TIER_NORMAL = "normal"
TIER_LOW = "low_anomaly"
TIER_SUSPICIOUS = "suspicious"
TIER_HIGH = "high"
TIER_CRITICAL = "critical"

HOLD_PATTERNS = {"B", "E", "F"}
REDUCTION_CHECKS = {
    "known_counterparties",
    "inbound_profile",
    "activity_abnormality",
    "onward_transfer_ratio",
    "reviewed_legitimate_pattern",
}

ACTION_ALLOW = "allow"
ACTION_MONITOR = "allow_monitor"
ACTION_STEP_UP = "step_up"
ACTION_HOLD = "hold_transaction"


def _fired(signals: list[dict], rule_id: str) -> bool:
    return any(signal["rule_id"] == rule_id for signal in signals)


def apply_family_dedup(signals: list[dict]) -> list[dict]:
    """Within a family, only the strongest signal scores. Others stay as evidence."""
    best: dict[str, int] = {}
    for index, signal in enumerate(signals):
        weight = signal["base_weight"] + signal.get("modifier", 0)
        current = best.get(signal["family"])
        if current is None or weight > signals[current]["base_weight"] + signals[current].get("modifier", 0):
            best[signal["family"]] = index
    scored = []
    for index, signal in enumerate(signals):
        item = dict(signal)
        if best.get(signal["family"]) == index:
            item["score_contribution"] = signal["base_weight"] + signal.get("modifier", 0)
        else:
            item["score_contribution"] = 0
        scored.append(item)
    return scored


def match_pattern(signals: list[dict], checks: list[dict]) -> str | None:
    by_id = {check["check"]: check for check in checks}
    r03 = _fired(signals, "R03")
    r08 = _fired(signals, "R08")
    r11 = _fired(signals, "R11")
    new_sender_mod = any(
        signal["rule_id"] == "R03" and signal.get("evidence", {}).get("new_sender_share", 0) >= settings.R03_NEW_SENDER_SHARE
        for signal in signals
    )
    if r03 and r08 and (r11 or new_sender_mod):
        return "B"
    if r08 and (_fired(signals, "R09") or _fired(signals, "R10")):
        return "E"
    if _fired(signals, "R10") and r08:
        return "E"
    if _fired(signals, "R07") and _fired(signals, "R05") and r11:
        return "F"
    if _fired(signals, "R02") and _fired(signals, "R01") and r11:
        return "C"
    if _fired(signals, "R06") and _fired(signals, "R02") and (r11 or _fired(signals, "R04")):
        return "D"

    def cleared(name: str) -> bool:
        check = by_id.get(name)
        return bool(check and check.get("cleared"))

    if r03 and cleared("onward_transfer_ratio") and cleared("sender_risk") and cleared("activity_abnormality"):
        return "A"
    if _fired(signals, "R10"):
        return "E"
    return None


def score(signals: list[dict], checks: list[dict], pattern: str | None) -> dict:
    strong = sum(
        signal["score_contribution"]
        for signal in signals
        if signal["severity"] == "strong"
    )
    other = sum(
        signal["score_contribution"]
        for signal in signals
        if signal["severity"] != "strong"
    )
    families = {signal["family"] for signal in signals if signal["score_contribution"] > 0}
    if len(families) >= 3:
        bonus = settings.FAMILY_BONUS_THREE
    elif len(families) == 2:
        bonus = settings.FAMILY_BONUS_TWO
    else:
        bonus = 0
    reduction = min(
        settings.CONTEXT_REDUCTION_CAP,
        settings.CONTEXT_REDUCTION
        * sum(1 for check in checks if check["check"] in REDUCTION_CHECKS and check.get("cleared")),
    )
    other_after = max(0, other + bonus - reduction)
    final = min(100, strong + other_after)
    if pattern == "A":
        final = min(final, 49)
    return {
        "strong": strong,
        "other": other,
        "combination_bonus": bonus,
        "reductions": reduction,
        "final": final,
    }


def tier_for(final: int, signals: list[dict], pattern: str | None) -> str:
    if final <= 29:
        return TIER_NORMAL
    if final <= 49:
        return TIER_LOW
    if final <= 69:
        return TIER_SUSPICIOUS
    if final <= 84:
        return TIER_HIGH
    has_strong = any(signal["severity"] == "strong" and signal["score_contribution"] > 0 for signal in signals)
    if has_strong:
        return TIER_CRITICAL
    return TIER_HIGH


def select_action(tier: str, pattern: str | None, signals: list[dict]) -> str:
    """Choose how much of the account to restrict. Detection stays separate from that choice."""
    del pattern
    if tier == TIER_CRITICAL and any(
        signal["severity"] == "strong" and signal["score_contribution"] > 0 for signal in signals
    ):
        return ACTION_HOLD
    if tier == TIER_HIGH:
        return ACTION_STEP_UP
    if tier == TIER_SUSPICIOUS:
        return ACTION_MONITOR
    return ACTION_ALLOW


def should_hold(tier: str, pattern: str | None, signals: list[dict]) -> bool:
    if tier == TIER_CRITICAL:
        return any(signal["severity"] == "strong" and signal["score_contribution"] > 0 for signal in signals)
    if tier == TIER_HIGH and pattern in HOLD_PATTERNS:
        return True
    return False
