"""
Reconciliation reports: the output of the Reconciliation Engine, which
validates the ledger independently of the Monitoring/fraud pipeline
(Architecture: Reconciliation operates directly on the Ledger Service).
"""
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin
from app.models.enums import ReconciliationStatus


class ReconciliationReport(Base, TimestampMixin):
    __tablename__ = "reconciliation_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[ReconciliationStatus] = mapped_column(nullable=False)
    accounts_checked: Mapped[int] = mapped_column(nullable=False)
    discrepancy_count: Mapped[int] = mapped_column(nullable=False, default=0)
    discrepancies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    triggered_by: Mapped[str] = mapped_column(default="manual", nullable=False)
