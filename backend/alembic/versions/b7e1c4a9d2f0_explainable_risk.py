"""explainable risk evaluations and amount holds

Revision ID: b7e1c4a9d2f0
Revises: 8aaeeb83ebab
Create Date: 2026-09-26 12:50:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e1c4a9d2f0"
down_revision: Union[str, None] = "8aaeeb83ebab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE alertstatus ADD VALUE IF NOT EXISTS 'CONFIRMED_FRAUD'")
    op.add_column("fraud_alerts", sa.Column("subject_user_id", sa.Integer(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("subject_role", sa.String(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("tier", sa.String(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("pattern", sa.String(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("signals", sa.JSON(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("context_checks", sa.JSON(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("score_breakdown", sa.JSON(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("rules_version", sa.String(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("user_explanation", sa.Text(), nullable=True))
    op.add_column("fraud_alerts", sa.Column("narrative", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_fraud_alerts_subject_user_id", "fraud_alerts", "users", ["subject_user_id"], ["id"]
    )
    op.create_table(
        "risk_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("subject_user_id", sa.Integer(), nullable=False),
        sa.Column("subject_role", sa.String(length=16), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("pattern", sa.String(length=8), nullable=True),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("context_checks", sa.JSON(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("rules_version", sa.String(length=16), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("hold_placed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subject_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_evaluations_transaction_id", "risk_evaluations", ["transaction_id"])
    op.create_index("ix_risk_evaluations_subject_user_id", "risk_evaluations", ["subject_user_id"])
    op.create_table(
        "amount_holds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "RELEASED", "EXPIRED", "CONFIRMED", name="holdstatus"), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_by", sa.Integer(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("narrative", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["fraud_alerts.id"]),
        sa.ForeignKeyConstraint(["released_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_amount_holds_user_id", "amount_holds", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_amount_holds_user_id", table_name="amount_holds")
    op.drop_table("amount_holds")
    op.drop_index("ix_risk_evaluations_subject_user_id", table_name="risk_evaluations")
    op.drop_index("ix_risk_evaluations_transaction_id", table_name="risk_evaluations")
    op.drop_table("risk_evaluations")
    op.drop_constraint("fk_fraud_alerts_subject_user_id", "fraud_alerts", type_="foreignkey")
    for column in (
        "narrative",
        "user_explanation",
        "rules_version",
        "score_breakdown",
        "context_checks",
        "signals",
        "pattern",
        "tier",
        "subject_role",
        "subject_user_id",
    ):
        op.drop_column("fraud_alerts", column)
