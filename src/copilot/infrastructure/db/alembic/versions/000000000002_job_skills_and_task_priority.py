"""Add job skills and review task priority columns.

Revision ID: 000000000002
Revises: 000000000001
Create Date: 2026-09-07 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000000000002"
down_revision: str | Sequence[str] | None = "000000000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs", sa.Column("skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
    )
    op.add_column(
        "review_tasks",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
    )


def downgrade() -> None:
    op.drop_column("review_tasks", "priority")
    op.drop_column("jobs", "skills")
