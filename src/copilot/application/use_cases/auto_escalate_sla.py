"""SLA timeout engine.

Two role-based windows govern a candidate's review task:

* **Triage SLA** (recruiter hours) — if the recruiter does not act in time the task
  is automatically forwarded to the Hiring Manager, who receives a fresh decision
  window.
* **Decision SLA** (manager hours) — if the manager does not act in time the task is
  automatically approved and its SLA timer is frozen.

The engine is invoked on a schedule by the infrastructure layer; all state changes
live in the domain model and persistence happens through the repository port.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from copilot.domain.sla_rule import Priority, resolve_sla_duration
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


async def _decision_hours(container: Container, job_id, priority: str) -> int:
    job_rule = await container.review_task_repository.get_sla_rule_for_job(job_id)
    _, decision_hours = resolve_sla_duration(Priority.from_str(priority), job_rule)
    return decision_hours


async def auto_escalate_sla(container: Container, now: datetime | None = None) -> dict:
    """Run one SLA timeout sweep. Returns a summary of the actions taken."""
    now = now or datetime.utcnow()
    correlation_id = get_correlation_id()

    forwarded = 0
    for task in await container.review_task_repository.list_breached_tasks("triage", now):
        if not task.auto_forward_to_manager(now):
            continue
        # Grant the manager a full decision window from the moment of escalation.
        hours = await _decision_hours(container, task.job_id, task.priority)
        task.decision_deadline_at = now + timedelta(hours=hours)
        await container.review_task_repository.update_task(task)
        await container.audit.log(
            action="sla_auto_forward",
            target_type="review_task",
            target_id=str(task.id),
            actor_id=None,
            actor_role="system",
            details={
                "to_status": task.status.value,
                "decision_hours": hours,
                "reason": "Recruiter triage SLA expired",
            },
            correlation_id=correlation_id,
        )
        forwarded += 1

    auto_approved = 0
    for task in await container.review_task_repository.list_breached_tasks("decision", now):
        if not task.auto_approve(now):
            continue
        await container.review_task_repository.update_task(task)
        await container.audit.log(
            action="sla_auto_approve",
            target_type="review_task",
            target_id=str(task.id),
            actor_id=None,
            actor_role="system",
            details={
                "to_status": task.status.value,
                "sla_outcome": task.sla_outcome,
                "reason": "Manager decision SLA expired",
            },
            correlation_id=correlation_id,
        )
        auto_approved += 1

    return {"forwarded": forwarded, "auto_approved": auto_approved}
