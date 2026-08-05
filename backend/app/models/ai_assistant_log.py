"""
AI Investigation Assistant audit log: every query/answer is recorded, per
idea.md's emphasis on the assistant reducing manual effort and improving
explainability - which requires a durable audit trail of what was asked
and what context/answer was given.
"""
from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class AiAssistantLog(Base, TimestampMixin):
    __tablename__ = "ai_assistant_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True, index=True
    )
    target_account_number: Mapped[str | None] = mapped_column(nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    context_used: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    admin_user: Mapped["User"] = relationship()  # noqa: F821
