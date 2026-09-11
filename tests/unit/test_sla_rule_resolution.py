"""Unit tests for SLA rule resolution order."""

from __future__ import annotations

from uuid import uuid4

from copilot.domain.job import Job
from copilot.domain.sla_rule import Priority, SLARule, resolve_sla_duration


def _job(priority: str = "MEDIUM") -> Job:
    return Job(
        id=uuid4(),
        title="Demo",
        department="Engineering",
        description="",
        location="Remote",
        priority=priority,
    )


def test_global_default_used_when_no_override() -> None:
    triage_hours, decision_hours = resolve_sla_duration(Priority.MEDIUM, job_rule=None)
    assert triage_hours == 48
    assert decision_hours == 48


def test_job_override_wins_over_global() -> None:
    job_rule = SLARule(
        id=uuid4(),
        job_id=uuid4(),
        priority=Priority.HIGH,
        triage_hours=12,
        decision_hours=18,
        active=True,
    )
    triage_hours, decision_hours = resolve_sla_duration(Priority.HIGH, job_rule=job_rule)
    assert triage_hours == 12
    assert decision_hours == 18


def test_inactive_override_ignored() -> None:
    job_rule = SLARule(
        id=uuid4(),
        job_id=uuid4(),
        priority=Priority.HIGH,
        triage_hours=12,
        decision_hours=18,
        active=False,
    )
    triage_hours, decision_hours = resolve_sla_duration(Priority.HIGH, job_rule=job_rule)
    assert triage_hours == 24
    assert decision_hours == 24
