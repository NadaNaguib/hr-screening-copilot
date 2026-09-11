"""Unit tests for SLA rule create/update (upsert) use case."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from copilot.application.use_cases.manage_sla_rules import create_or_update_sla_rule
from copilot.domain.errors import AuthorizationError
from copilot.domain.sla_rule import SLARule


class _FakeDocRepo:
    def __init__(self) -> None:
        self.saved: SLARule | None = None
        self.existing: list[SLARule] = []

    async def save_sla_rule(self, rule: SLARule) -> SLARule:
        self.saved = rule
        return rule

    async def list_sla_rules(self, active_only: bool = False) -> list[SLARule]:
        return list(self.existing)


def _container(repo: _FakeDocRepo) -> SimpleNamespace:
    return SimpleNamespace(document_repository=repo)


async def test_create_rule_normalizes_custom_priority() -> None:
    repo = _FakeDocRepo()
    result = await create_or_update_sla_rule(
        container=_container(repo),
        role="admin",
        job_id=None,
        priority="critical",
        triage_hours=6,
        decision_hours=12,
    )
    assert repo.saved is not None
    assert repo.saved.priority == "CRITICAL"
    assert result["priority"] == "CRITICAL"
    assert result["triage_hours"] == 6


async def test_update_rule_reuses_existing_id() -> None:
    repo = _FakeDocRepo()
    rule_id = uuid4()
    result = await create_or_update_sla_rule(
        container=_container(repo),
        role="admin",
        job_id=None,
        priority="high",
        triage_hours=8,
        decision_hours=16,
        rule_id=rule_id,
    )
    assert repo.saved is not None
    assert repo.saved.id == rule_id
    assert result["id"] == str(rule_id)
    assert result["priority"] == "HIGH"


async def test_non_admin_cannot_write_rules() -> None:
    repo = _FakeDocRepo()
    with pytest.raises(AuthorizationError):
        await create_or_update_sla_rule(
            container=_container(repo),
            role="hr_recruiter",
            job_id=None,
            priority="high",
            triage_hours=8,
            decision_hours=16,
        )
    assert repo.saved is None


async def test_update_preserves_created_at_and_job_scope() -> None:
    repo = _FakeDocRepo()
    rule_id = uuid4()
    job_id = uuid4()
    original_created = datetime(2020, 1, 1)
    repo.existing = [
        SLARule(
            id=rule_id,
            job_id=job_id,
            priority="LOW",
            triage_hours=72,
            decision_hours=72,
            created_at=original_created,
        )
    ]

    result = await create_or_update_sla_rule(
        container=_container(repo),
        role="admin",
        job_id=None,  # omitted by the client -> keep the existing scope
        priority="low",
        triage_hours=48,
        decision_hours=48,
        rule_id=rule_id,
    )

    assert repo.saved is not None
    assert repo.saved.created_at == original_created
    assert repo.saved.job_id == job_id
    assert result["triage_hours"] == 48
