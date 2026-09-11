"""Recruiter triage actions on a review task."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from copilot.domain.errors import AuthorizationError, NotFoundError
from copilot.domain.review_task import ReviewAction, ReviewStatus
from copilot.domain.sla_rule import Priority, resolve_sla_duration
from copilot.infrastructure.di import Container
from copilot.infrastructure.observability.correlation import get_correlation_id


async def triage_candidate(
    container: Container,
    actor_id: UUID,
    role: str,
    task_id: UUID,
    action: str,
    reason: str | None = None,
    correlation_id: str = "",
) -> dict:
    if role not in {"hr_recruiter", "admin"}:
        raise AuthorizationError("Only hr_recruiter or admin can triage")
    correlation_id = correlation_id or get_correlation_id()
    task = await container.review_task_repository.get_task(task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")

    review_action = ReviewAction(action)
    task.apply_action(role, review_action, reason=reason, actor_id=actor_id)

    if task.status == ReviewStatus.PENDING_MANAGER_REVIEW:
        # Set decision SLA deadline
        job = await container.document_repository.get_job(task.job_id) if task.job_id else None
        priority = Priority.from_str(job.priority if job else "MEDIUM")
        job_rule = await container.review_task_repository.get_sla_rule_for_job(task.job_id)
        _, decision_hours = resolve_sla_duration(priority, job_rule)
        task.decision_deadline_at = datetime.utcnow() + timedelta(hours=decision_hours)

    await container.review_task_repository.update_task(task)
    await container.audit.log(
        action=f"triage_{action}",
        target_type="review_task",
        target_id=str(task.id),
        actor_id=actor_id,
        actor_role=role,
        details={"reason": reason, "to_status": task.status.value},
        correlation_id=correlation_id,
    )
    return {
        "task_id": str(task.id),
        "status": task.status.value,
        "audit_log": task.audit_log,
    }
