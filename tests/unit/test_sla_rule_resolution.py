"""Unit tests for SLA rule resolution order."""

from __future__ import annotations

from uuid import uuid4

from copilot.domain.job import Job
from copilot.domain.sla_rule import Priority, SLARule, normalize_priority, resolve_sla_duration


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


def test_normalize_priority_uppercases_and_defaults() -> None:
    assert normalize_priority("high") == "HIGH"
    assert normalize_priority("  Critical ") == "CRITICAL"
    assert normalize_priority(Priority.LOW) == "LOW"
    assert normalize_priority("") == "MEDIUM"
    assert normalize_priority(None) == "MEDIUM"


def test_sla_rule_preserves_custom_priority_uppercase() -> None:
    rule = SLARule(priority="critical", triage_hours=6, decision_hours=9)
    assert rule.priority == "CRITICAL"
    assert rule.to_dict()["priority"] == "CRITICAL"


def test_sla_rule_accepts_enum_priority() -> None:
    assert SLARule(priority=Priority.HIGH).priority == "HIGH"
