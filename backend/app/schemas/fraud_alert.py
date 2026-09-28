from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AlertStatus, HoldStatus


class TriggeredRule(BaseModel):
    rule_name: str
    explanation: str
    risk_weight: int


class SignalOut(BaseModel):
    rule_id: str
    rule_name: str
    version: int = 1
    family: str = ""
    severity: str = "soft"
    score_contribution: int = 0
    explanation: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class ContextCheckOut(BaseModel):
    check: str
    value: Any = None
    threshold: Any = None
    cleared: bool = False


class FraudAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    user_id: int
    account_number: str
    transaction_public_id: str
    risk_score: int
    triggered_rules: list[TriggeredRule]
    status: AlertStatus
    created_at: datetime
    subject_role: str | None = None
    tier: str | None = None
    pattern: str | None = None
    signals: list[SignalOut] = Field(default_factory=list)
    context_checks: list[ContextCheckOut] = Field(default_factory=list)
    score_breakdown: dict[str, Any] | None = None
    narrative: str | None = None
    user_explanation: str | None = None
    hold_amount: str | None = None
    hold_status: str | None = None
    decision_trace: dict[str, Any] | None = None
    outcome: str | None = None


class RuleStat(BaseModel):
    rule_id: str
    alerts: int
    false_positives: int


class PatternFeedback(BaseModel):
    matched: int
    stayed_under_alert: int
    later_confirmed: int


class HoldResponse(BaseModel):
    id: int
    amount: str
    status: HoldStatus
    kind: str = "risk"
    reason_codes: list[str]
    expires_at: datetime
    explanation_due_at: datetime
    narrative: str | None = None
    user_explanation: str | None = None


class ExplanationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
