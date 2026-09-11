"""Unit tests for the SLA auto-escalation engine."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from copilot.application.use_cases.auto_escalate_sla import auto_escalate_sla
from copilot.domain.review_task import ReviewStatus, ReviewTask


class _FakeReviewTaskRepo:
    def __init__(self, triage: list, decision: list, job_rule=None) -> None:
        self._by_stage = {"triage": triage, "decision": decision}
        self._job_rule = job_rule
        self.updated: list[ReviewTask] = []

    async def list_breached_tasks(self, stage: str, now: datetime) -> list:
        return list(self._by_stage.get(stage, []))

    async def get_sla_rule_for_job(self, job_id):
        return self._job_rule

    async def update_task(self, task: ReviewTask) -> ReviewTask:
        self.updated.append(task)
        return task


class _FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def log(self, **kwargs) -> None:
        self.events.append(kwargs)


class _FakeContainer:
    def __init__(self, repo: _FakeReviewTaskRepo, audit: _FakeAudit) -> None:
        self.review_task_repository = repo
        self.audit = audit


async def test_auto_escalation_forwards_triage_and_approves_decision() -> None:
    now = datetime.utcnow()
    triage_task = ReviewTask(
        candidate_id=uuid4(), status=ReviewStatus.PENDING_TRIAGE, priority="HIGH"
    )
    decision_task = ReviewTask(
        candidate_id=uuid4(), status=ReviewStatus.PENDING_MANAGER_REVIEW, priority="LOW"
    )
    decision_task.decision_deadline_at = now - timedelta(hours=1)

    repo = _FakeReviewTaskRepo([triage_task], [decision_task])
    audit = _FakeAudit()
    container = _FakeContainer(repo, audit)

    result = await auto_escalate_sla(container, now=now)

    assert result == {"forwarded": 1, "auto_approved": 1}
    # Recruiter timeout -> forwarded to the manager with a fresh decision window.
    assert triage_task.status == ReviewStatus.PENDING_MANAGER_REVIEW
    assert triage_task.decision_deadline_at is not None
    assert triage_task.decision_deadline_at > now
    # Manager timeout -> auto-approved and SLA frozen as breached.
    assert decision_task.status == ReviewStatus.APPROVED
    assert decision_task.sla_outcome == "breached"
    assert decision_task.sla_frozen_at is not None

    assert len(repo.updated) == 2
    assert [e["action"] for e in audit.events] == ["sla_auto_forward", "sla_auto_approve"]


async def test_auto_escalation_noop_when_nothing_breached() -> None:
    repo = _FakeReviewTaskRepo([], [])
    container = _FakeContainer(repo, _FakeAudit())
    result = await auto_escalate_sla(container)
    assert result == {"forwarded": 0, "auto_approved": 0}
    assert repo.updated == []
