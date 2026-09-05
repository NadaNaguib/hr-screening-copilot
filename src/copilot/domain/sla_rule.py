"""SLA rule domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from copilot.domain.errors import ValidationError


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_GLOBAL_SLA_HOURS: dict[Priority, int] = {
    Priority.HIGH: 24,
    Priority.MEDIUM: 48,
    Priority.LOW: 72,
}


@dataclass
class SLARule:
    id: UUID = field(default_factory=uuid4)
    job_id: UUID | None = None
    priority: Priority = Priority.MEDIUM
    triage_hours: int = 24
    decision_hours: int = 48
    active: bool = True
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def triage_delta(self) -> timedelta:
        return timedelta(hours=self.triage_hours)

    def decision_delta(self) -> timedelta:
        return timedelta(hours=self.decision_hours)

    def apply_to_job(self, job_id: UUID) -> SLARule:
        if self.job_id is not None:
            raise ValidationError("Rule already scoped to a job")
        return SLARule(
            job_id=job_id,
            priority=self.priority,
            triage_hours=self.triage_hours,
            decision_hours=self.decision_hours,
            active=self.active,
            created_by=self.created_by,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id) if self.job_id else None,
            "priority": self.priority.value,
            "triage_hours": self.triage_hours,
            "decision_hours": self.decision_hours,
            "active": self.active,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def default_sla_rule(priority: Priority = Priority.MEDIUM) -> SLARule:
    return SLARule(
        priority=priority,
        triage_hours=_GLOBAL_SLA_HOURS[priority],
        decision_hours=_GLOBAL_SLA_HOURS[priority],
    )


def resolve_sla_duration(priority: Priority, job_rule: SLARule | None) -> tuple[int, int]:
    if job_rule is not None and job_rule.active:
        return job_rule.triage_hours, job_rule.decision_hours
    rule = default_sla_rule(priority)
    return rule.triage_hours, rule.decision_hours
