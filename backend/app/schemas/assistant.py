from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class AskAssistantRequest(BaseModel):
    question: str
    transaction_id: str | None = None
    account_number: str | None = None

    @model_validator(mode="after")
    def require_one_target(self) -> "AskAssistantRequest":
        if not self.transaction_id and not self.account_number:
            raise ValueError("Either transaction_id or account_number must be provided")
        return self


class AssistantLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    transaction_id: int | None
    target_account_number: str | None
    created_at: datetime
