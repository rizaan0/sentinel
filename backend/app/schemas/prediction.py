from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskLevel


class ForecastPoint(BaseModel):
    offset: int
    score: int
    kind: str


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
    current_risk: int = 0
    predicted_7d_risk: int = 0
    risk_change: int = 0
    trend: str = "stable"
    horizon_days: int = 7
    series: list[ForecastPoint] = []
    drivers: list[str] = []
    explanation: str = ""
