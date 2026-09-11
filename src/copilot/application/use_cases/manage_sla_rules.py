"""Admin CRUD for SLA rules."""

from __future__ import annotations

from uuid import UUID

from copilot.domain.errors import AuthorizationError, NotFoundError, ValidationError
from copilot.domain.sla_rule import SLARule, normalize_priority
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
                priority=normalize_priority(orm.priority),
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
    rule_id: UUID | None = None,
) -> dict:
    """Create a new SLA rule, or update the existing one when ``rule_id`` is given."""
    if role != "admin":
        raise AuthorizationError("Only admin can edit SLA rules")

    if triage_hours < 1 or decision_hours < 1:
        raise ValidationError("SLA hours must be at least 1")

    created_at = None
    if rule_id is not None:
        # Preserve provenance/scope of the row being updated.
        existing = {r.id: r for r in await container.document_repository.list_sla_rules()}
        current = existing.get(rule_id)
        if current is not None:
            created_at = current.created_at
            if job_id is None:
                job_id = current.job_id

    kwargs: dict = {
        "job_id": job_id,
        "priority": normalize_priority(priority),
        "triage_hours": triage_hours,
        "decision_hours": decision_hours,
        "active": active,
        "created_by": created_by,
    }
    if rule_id is not None:
        kwargs["id"] = rule_id
    if created_at is not None:
        kwargs["created_at"] = created_at

    rule = SLARule(**kwargs)
    saved = await container.document_repository.save_sla_rule(rule)
    return saved.to_dict()


async def delete_sla_rule(container: Container, role: str, rule_id: UUID) -> dict:
    """Delete an SLA rule. Admin-only."""
    if role != "admin":
        raise AuthorizationError("Only admin can delete SLA rules")
    deleted = await container.document_repository.delete_sla_rule(rule_id)
    if not deleted:
        raise NotFoundError(f"SLA rule {rule_id} not found")
    return {"id": str(rule_id), "deleted": True}


async def list_active_sla_priorities(container: Container, role: str) -> list[str]:
    """Return the distinct priority levels from active SLA rules (for UI filters)."""
    if role not in {"admin", "hiring_manager", "hr_recruiter"}:
        raise AuthorizationError("Not authorized")
    rules = await container.document_repository.list_sla_rules(active_only=True)
    priorities: list[str] = []
    for rule in rules:
        value = normalize_priority(rule.priority)
        if value not in priorities:
            priorities.append(value)
    return priorities
