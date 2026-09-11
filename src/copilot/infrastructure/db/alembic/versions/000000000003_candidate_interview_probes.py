"""Add interview probes columns to candidates.

Revision ID: 000000000003
Revises: 000000000002
Create Date: 2026-09-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000003"
down_revision: str | Sequence[str] | None = "000000000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("interview_probes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "candidates",
        sa.Column("probes_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("candidates", "probes_generated")
    op.drop_column("candidates", "interview_probes")
