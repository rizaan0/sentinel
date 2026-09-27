"""7-day risk forecast fields

Revision ID: c4d8e2a1b6f3
Revises: b7e1c4a9d2f0
Create Date: 2026-09-26 14:55:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d8e2a1b6f3"
down_revision: Union[str, None] = "b7e1c4a9d2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risk_predictions", sa.Column("current_risk", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("risk_predictions", sa.Column("predicted_7d_risk", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("risk_predictions", sa.Column("risk_change", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("risk_predictions", sa.Column("trend", sa.String(length=16), nullable=False, server_default="stable"))
    op.add_column("risk_predictions", sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="7"))
    op.add_column("risk_predictions", sa.Column("series", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("risk_predictions", sa.Column("drivers", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("risk_predictions", sa.Column("explanation", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    for column in (
        "explanation",
        "drivers",
        "series",
        "horizon_days",
        "trend",
        "risk_change",
        "predicted_7d_risk",
        "current_risk",
    ):
        op.drop_column("risk_predictions", column)
