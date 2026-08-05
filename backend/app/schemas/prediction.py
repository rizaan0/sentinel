from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskLevel


class RiskPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    account_number: str
    predicted_risk_level: RiskLevel
    trend_score: float
    alerts_last_7d: int
    alerts_prior_7d: int
    avg_risk_score_last_7d: float
    created_at: datetime
