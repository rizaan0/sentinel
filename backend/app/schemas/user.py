from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class UserPublic(BaseModel):
    """Safe, outward-facing representation of a user. Never includes secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    account_number: str
    role: UserRole
    pin_is_set: bool
    balance: Decimal


class UserSearchResult(BaseModel):
    """Minimal, masked info returned when searching recipients (Phase 2)."""

    model_config = ConfigDict(from_attributes=True)

    account_number: str
    full_name: str
