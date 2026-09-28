"""One investigator or system action on a case, kept so the timeline can be rebuilt."""

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class CaseEvent(Base, TimestampMixin):
    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("fraud_alerts.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
