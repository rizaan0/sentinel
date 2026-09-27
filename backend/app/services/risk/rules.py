"""Versioned fraud-rule registry. A firing rule is a signal, never a verdict."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSpec:
    id: str
    name: str
    version: int
    family: str
    severity: str  # soft | medium | strong
    base_weight: int
    summary: str


RULES: dict[str, RuleSpec] = {
    "R01": RuleSpec(
        "R01",
        "Rapid Same-Pair Transfers",
        1,
        "velocity",
        "soft",
        10,
        "Repeated transfers between the same two accounts in a short window.",
    ),
    "R02": RuleSpec(
        "R02",
        "Account Transaction Velocity",
        1,
        "velocity",
        "medium",
        20,
        "Transaction count far above this account's usual rate.",
    ),
    "R03": RuleSpec(
        "R03",
        "Fan-In Burst",
        1,
        "fan",
        "soft",
        15,
        "Many distinct accounts sent money to one recipient in a short window.",
    ),
    "R04": RuleSpec(
        "R04",
        "Fan-Out Burst",
        1,
        "fan",
        "medium",
        20,
        "One account sent money to many recipients in a short window.",
    ),
    "R05": RuleSpec(
        "R05",
        "Unusually Large Transaction",
        1,
        "amount",
        "medium",
        25,
        "Amount is far above this sender's own typical transfer.",
    ),
    "R06": RuleSpec(
        "R06",
        "Structured Small Transactions",
        1,
        "amount",
        "medium",
        20,
        "Many small transfers whose combined value is unusual.",
    ),
    "R07": RuleSpec(
        "R07",
        "Dormant Reactivation",
        1,
        "velocity",
        "medium",
        20,
        "An idle account suddenly resumed with a burst of activity.",
    ),
    "R08": RuleSpec(
        "R08",
        "Rapid Inbound to Outbound",
        1,
        "flow",
        "strong",
        35,
        "Most of the money just received was sent onward within minutes.",
    ),
    "R09": RuleSpec(
        "R09",
        "Circular Fund Flow",
        1,
        "flow",
        "strong",
        35,
        "Funds looped back to the originating account through other accounts.",
    ),
    "R10": RuleSpec(
        "R10",
        "Money-Mule Chain",
        1,
        "flow",
        "strong",
        45,
        "The same funds passed through several accounts, each keeping very little.",
    ),
    "R11": RuleSpec(
        "R11",
        "New-Counterparty Burst",
        1,
        "counterparty",
        "soft",
        15,
        "The account suddenly transacted with many accounts it had never used.",
    ),
    "R12": RuleSpec(
        "R12",
        "Counterparty Concentration Change",
        1,
        "counterparty",
        "soft",
        10,
        "Recent transfers concentrated on one recipient outside the usual set.",
    ),
    "ML": RuleSpec(
        "ML",
        "ML Anomaly",
        1,
        "model",
        "soft",
        15,
        "The anomaly model scored this transfer as unusual for the account.",
    ),
}

RULES_VERSION = "1"
