"""Resolve SLA deadline for a review task entering a stage."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from copilot.domain.sla_rule import Priority, resolve_sla_duration
from copilot.infrastructure.di import Container


async def resolve_sla_deadline(
    container: Container,
    job_id: UUID | None,
    priority: str,
    stage: str,  # triage or decision
) -> datetime:
    job_rule = await container.review_task_repository.get_sla_rule_for_job(job_id)
    triage_hours, decision_hours = resolve_sla_duration(Priority.from_str(priority), job_rule)
    hours = triage_hours if stage == "triage" else decision_hours
    return datetime.utcnow() + timedelta(hours=hours)
