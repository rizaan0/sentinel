"""Scoped containment, decision traces, and case events.

Revision ID: d5e9f3b2c7a1
Revises: c4d8e2a1b6f3
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e9f3b2c7a1"
down_revision: Union[str, None] = "c4d8e2a1b6f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE transactionstatus ADD VALUE IF NOT EXISTS 'HELD'")
    op.execute("ALTER TYPE transactionstatus ADD VALUE IF NOT EXISTS 'REJECTED'")
    op.execute("ALTER TYPE transactionstatus ADD VALUE IF NOT EXISTS 'held'")
    op.execute("ALTER TYPE transactionstatus ADD VALUE IF NOT EXISTS 'rejected'")
    op.add_column("transactions", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
    op.create_index("ix_transactions_idempotency_key", "transactions", ["idempotency_key"], unique=True)
    op.add_column("amount_holds", sa.Column("transaction_id", sa.Integer(), nullable=True))
    op.add_column("amount_holds", sa.Column("kind", sa.String(length=32), nullable=False, server_default="risk"))
    op.create_foreign_key("fk_amount_holds_transaction_id", "amount_holds", "transactions", ["transaction_id"], ["id"])
    op.add_column("risk_evaluations", sa.Column("decision_trace", sa.JSON(), nullable=True))
    op.add_column("risk_evaluations", sa.Column("outcome", sa.String(length=64), nullable=True))
    op.add_column("fraud_alerts", sa.Column("decision_trace", sa.JSON(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("outcome", sa.String(length=64), nullable=True))
    op.create_table(
        "step_up_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_account_number", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("remark", sa.String(length=280), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("evaluation", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_step_up_challenges_public_id", "step_up_challenges", ["public_id"], unique=True)
    op.create_index("ix_step_up_challenges_sender_id", "step_up_challenges", ["sender_id"])
    op.create_table(
        "account_restrictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("fraud_alerts.id"), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="outgoing"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reason", sa.String(length=280), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_account_restrictions_user_id", "account_restrictions", ["user_id"])
    op.create_table(
        "case_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("fraud_alerts.id"), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_events_alert_id", "case_events", ["alert_id"])


def downgrade() -> None:
    op.drop_table("case_events")
    op.drop_table("account_restrictions")
    op.drop_table("step_up_challenges")
    op.drop_column("fraud_alerts", "outcome")
    op.drop_column("fraud_alerts", "decision_trace")
    op.drop_column("risk_evaluations", "outcome")
    op.drop_column("risk_evaluations", "decision_trace")
    op.drop_constraint("fk_amount_holds_transaction_id", "amount_holds", type_="foreignkey")
    op.drop_column("amount_holds", "kind")
    op.drop_column("amount_holds", "transaction_id")
    op.drop_index("ix_transactions_idempotency_key", table_name="transactions")
    op.drop_column("transactions", "idempotency_key")
