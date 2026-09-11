"""Update review task priority and reset the SLA countdown."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from copilot.domain.errors import NotFoundError, ValidationError
from copilot.domain.review_task import (
    SLA_PHASE_DECISION,
    SLA_PHASE_TRIAGE,
    utc_iso,
)
from copilot.domain.sla_rule import Priority, normalize_priority, resolve_sla_duration
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


async def update_task_priority(
    container: Container,
    actor_id: UUID,
    role: str,
    task_id: UUID,
    priority: str,
    correlation_id: str = "",
) -> dict:
    """Change a task's priority (and its candidate) and restart the phase SLA timer."""
    correlation_id = correlation_id or get_correlation_id()
    task = await container.review_task_repository.get_task(task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")

    if not (priority or "").strip():
        raise ValidationError("Priority is required")
    priority_upper = normalize_priority(priority)
    task.priority = priority_upper
    # Single, explicit UTC reference for the whole recalculation. We keep the
    # stored value naive (DB column is TIMESTAMP WITHOUT TIME ZONE) but derive it
    # from an aware UTC instant so the duration is exactly N hours.
    now = datetime.now(UTC).replace(tzinfo=None)
    task.updated_at = now

    # Recalculate the SLA deadline for the current phase using the new priority.
    sla_phase = task.sla_phase()
    if not task.is_resolved() and sla_phase in (SLA_PHASE_TRIAGE, SLA_PHASE_DECISION):
        job_rule = await container.review_task_repository.get_sla_rule_for_job(task.job_id)
        triage_hours, decision_hours = resolve_sla_duration(
            Priority.from_str(priority_upper), job_rule
        )
        hours = triage_hours if sla_phase == SLA_PHASE_TRIAGE else decision_hours
        new_deadline = now + timedelta(hours=hours)
        if sla_phase == SLA_PHASE_TRIAGE:
            task.triage_deadline_at = new_deadline
        else:
            task.decision_deadline_at = new_deadline
        # Reopen the countdown if it had previously been frozen.
        task.sla_frozen_at = None
        task.sla_outcome = None

    task = await container.review_task_repository.update_task(task)

    # Keep the candidate record in sync with the task priority.
    candidate = await container.candidate_repository.get_candidate(task.candidate_id)
    if candidate is not None and candidate.priority != priority_upper:
        candidate.priority = priority_upper
        await container.candidate_repository.update_candidate(candidate)

    await container.audit.log(
        action="update_task_priority",
        target_type="review_task",
        target_id=str(task.id),
        actor_id=actor_id,
        actor_role=role,
        details={
            "priority": priority_upper,
            "sla_phase": task.sla_phase(),
        },
        correlation_id=correlation_id,
    )

    deadline = task.active_sla_deadline()
    return {
        "id": str(task.id),
        "priority": task.priority,
        "sla_phase": task.sla_phase(),
        "sla_deadline_at": utc_iso(deadline),
        "sla_active": deadline is not None and task.sla_frozen_at is None,
        "updated_at": utc_iso(task.updated_at),
    }
