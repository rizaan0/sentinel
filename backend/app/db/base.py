"""
Import all models here so Alembic's autogenerate can discover them via
Base.metadata. Populated as models are added phase by phase.
"""
from app.db.base_class import Base  # noqa: F401
from app.models.ai_assistant_log import AiAssistantLog  # noqa: F401
from app.models.fraud_alert import FraudAlert  # noqa: F401
from app.models.ledger_entry import LedgerEntry  # noqa: F401
from app.models.pin_credential import PinCredential  # noqa: F401
from app.models.reconciliation_report import ReconciliationReport  # noqa: F401
from app.models.risk_prediction import RiskPrediction  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.wallet import Wallet  # noqa: F401
