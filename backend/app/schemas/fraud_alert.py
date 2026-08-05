from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertStatus


class TriggeredRule(BaseModel):
    rule_name: str
    explanation: str
    risk_weight: int


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
