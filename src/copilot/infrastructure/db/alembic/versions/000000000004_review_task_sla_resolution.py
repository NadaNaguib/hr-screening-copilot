"""Add SLA resolution/freeze columns to review tasks.

Revision ID: 000000000004
Revises: 000000000003
Create Date: 2026-09-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000004"
down_revision: str | Sequence[str] | None = "000000000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "review_tasks",
        sa.Column("sla_frozen_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "review_tasks",
        sa.Column("sla_outcome", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("review_tasks", "sla_outcome")
    op.drop_column("review_tasks", "sla_frozen_at")
