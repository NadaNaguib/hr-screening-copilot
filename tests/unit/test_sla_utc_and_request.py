"""Tests for UTC-safe SLA serialization and the SLA-rule request schema."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from copilot.domain.review_task import utc_iso
from copilot.presentation.routers.admin_sla_rules import SLARuleRequest


def test_utc_iso_marks_naive_utc_with_offset() -> None:
    naive = datetime(2026, 9, 11, 12, 0, 0)
    assert utc_iso(naive) == "2026-09-11T12:00:00+00:00"


def test_utc_iso_converts_aware_values_to_utc() -> None:
    cairo = timezone(timedelta(hours=3))
    aware = datetime(2026, 9, 11, 15, 0, 0, tzinfo=cairo)
    assert utc_iso(aware) == "2026-09-11T12:00:00+00:00"


def test_utc_iso_none_passthrough() -> None:
    assert utc_iso(None) is None


def test_utc_iso_preserves_full_duration() -> None:
    """A 24h window must render as 24h once parsed back with an offset."""
    deadline = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24)
    parsed = datetime.fromisoformat(utc_iso(deadline))
    assert parsed.tzinfo is not None
    assert timedelta(hours=23, minutes=59) < parsed - datetime.now(UTC) <= timedelta(hours=24)


def test_sla_request_treats_blank_ids_as_none() -> None:
    request = SLARuleRequest(
        id="",
        job_id="   ",
        priority="  low  ",
        triage_hours=72,
        decision_hours=72,
    )
    assert request.id is None
    assert request.job_id is None
    assert request.priority == "low"
    assert request.active is True


def test_sla_request_accepts_omitted_optional_ids() -> None:
    request = SLARuleRequest(priority="HIGH", triage_hours=24, decision_hours=24)
    assert request.id is None
    assert request.job_id is None
