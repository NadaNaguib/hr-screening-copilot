"""Admin CRUD for SLA rules."""
from __future__ import annotations

from uuid import UUID

from copilot.domain.errors import AuthorizationError
from copilot.domain.sla_rule import Priority, SLARule
from copilot.infrastructure.di import Container


async def list_sla_rules(container: Container, role: str) -> list[dict]:
    if role not in {"admin", "hiring_manager", "hr_recruiter"}:
        raise AuthorizationError("Not authorized")
    from sqlalchemy import select

    from copilot.infrastructure.db.models import SLARuleORM

    result = await container.session.execute(select(SLARuleORM))
    rules = []
    for orm in result.scalars().all():
        rules.append(
            SLARule(
                id=orm.id,
                job_id=orm.job_id,
                priority=Priority(orm.priority),
                triage_hours=orm.triage_hours,
                decision_hours=orm.decision_hours,
                active=orm.active,
                created_by=orm.created_by,
                created_at=orm.created_at,
                updated_at=orm.updated_at,
            ).to_dict()
        )
    return rules


async def create_or_update_sla_rule(
    container: Container,
    role: str,
    job_id: UUID | None,
    priority: str,
    triage_hours: int,
    decision_hours: int,
    active: bool = True,
    created_by: UUID | None = None,
) -> dict:
    if role != "admin":
        raise AuthorizationError("Only admin can edit SLA rules")

    rule = SLARule(
        job_id=job_id,
        priority=Priority(priority.lower()),
        triage_hours=triage_hours,
        decision_hours=decision_hours,
        active=active,
        created_by=created_by,
    )
    saved = await container.document_repository.save_sla_rule(rule)
    return saved.to_dict()
