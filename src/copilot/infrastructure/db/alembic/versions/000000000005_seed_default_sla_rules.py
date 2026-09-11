"""Seed default global SLA rules (HIGH / MEDIUM / LOW).

Revision ID: 000000000005
Revises: 000000000004
Create Date: 2026-09-11 00:00:00.000000

Idempotently ensures the system ships with active *global* SLA defaults so the
priority dropdowns and SLA resolution work out of the box:

* HIGH   — 24h triage / 24h decision
* MEDIUM — 48h triage / 48h decision
* LOW    — 72h triage / 72h decision

Each insert is guarded by an existence check on ``(job_id IS NULL, priority)`` so
job-scoped overrides and user-created rules are never touched.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from alembic import op
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    select,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision: str = "000000000005"
down_revision: str | Sequence[str] | None = "000000000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_RULES: list[tuple[str, int, int]] = [
    ("HIGH", 24, 24),
    ("MEDIUM", 48, 48),
    ("LOW", 72, 72),
]

_sla_rules = Table(
    "sla_rules",
    MetaData(),
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    Column("job_id", PGUUID(as_uuid=True), nullable=True),
    Column("priority", String(length=20), nullable=False),
    Column("triage_hours", Integer, nullable=False),
    Column("decision_hours", Integer, nullable=False),
    Column("active", Boolean, nullable=False),
    Column("created_by", PGUUID(as_uuid=True), nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC).replace(tzinfo=None)
    for priority, triage_hours, decision_hours in _DEFAULT_RULES:
        exists = bind.execute(
            select(_sla_rules.c.id)
            .where(
                _sla_rules.c.job_id.is_(None),
                _sla_rules.c.priority == priority,
            )
            .limit(1)
        ).first()
        if exists:
            continue
        bind.execute(
            _sla_rules.insert().values(
                id=uuid4(),
                job_id=None,
                priority=priority,
                triage_hours=triage_hours,
                decision_hours=decision_hours,
                active=True,
                created_by=None,
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    # Removes only the seeded global defaults; job-scoped rules are preserved.
    bind = op.get_bind()
    bind.execute(
        _sla_rules.delete().where(
            _sla_rules.c.job_id.is_(None),
            _sla_rules.c.priority.in_([p for p, _, _ in _DEFAULT_RULES]),
        )
    )
