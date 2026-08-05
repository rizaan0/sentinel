from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ReconciliationStatus


class ReconciliationDiscrepancy(BaseModel):
    user_id: int
    account_number: str
    expected_balance: str
    actual_balance: str
    difference: str


class ReconciliationReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ReconciliationStatus
    accounts_checked: int
    discrepancy_count: int
    discrepancies: list[ReconciliationDiscrepancy]
    triggered_by: str
    created_at: datetime
