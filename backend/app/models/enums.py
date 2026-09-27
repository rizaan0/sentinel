"""
Shared enums used across models.
"""
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class TransactionStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class LedgerEntryType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class LedgerReferenceType(str, enum.Enum):
    GENESIS = "genesis"  # initial 1000 ST Coins granted at signup
    TRANSFER = "transfer"


class ReconciliationStatus(str, enum.Enum):
    CLEAN = "clean"
    DISCREPANCIES_FOUND = "discrepancies_found"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    CONFIRMED_FRAUD = "confirmed_fraud"


class HoldStatus(str, enum.Enum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"
    CONFIRMED = "confirmed"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
