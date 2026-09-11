"""Unit tests for Review Queue priority change -> SLA timer reset."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from copilot.application.use_cases.update_task_priority import update_task_priority
from copilot.domain.candidate import Candidate
from copilot.domain.review_task import ReviewStatus, ReviewTask


class _FakeReviewTaskRepo:
    def __init__(self, task: ReviewTask) -> None:
        self._task = task
        self.updated = 0

    async def get_task(self, task_id):
        return self._task if self._task.id == task_id else None

    async def get_sla_rule_for_job(self, job_id):
        return None

    async def update_task(self, task: ReviewTask) -> ReviewTask:
        self.updated += 1
        return task


class _FakeCandidateRepo:
    def __init__(self, candidate: Candidate) -> None:
        self._candidate = candidate
        self.updated = 0

    async def get_candidate(self, candidate_id):
        return self._candidate if self._candidate.id == candidate_id else None

    async def update_candidate(self, candidate: Candidate) -> Candidate:
        self.updated += 1
        return candidate


class _FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def log(self, **kwargs) -> None:
        self.events.append(kwargs)


class _FakeContainer:
    def __init__(self, task_repo, candidate_repo, audit) -> None:
        self.review_task_repository = task_repo
        self.candidate_repository = candidate_repo
        self.audit = audit


async def test_priority_change_resets_active_timer() -> None:
    candidate_id, job_id = uuid4(), uuid4()
    task = ReviewTask(
        candidate_id=candidate_id,
        job_id=job_id,
        status=ReviewStatus.PENDING_TRIAGE,
        priority="LOW",
    )
    task.triage_deadline_at = datetime.utcnow() - timedelta(hours=5)
    task.sla_frozen_at = datetime.utcnow()
    task.sla_outcome = "breached"
    candidate = Candidate(id=candidate_id, full_name="Alex", priority="LOW")

    task_repo = _FakeReviewTaskRepo(task)
    candidate_repo = _FakeCandidateRepo(candidate)
    audit = _FakeAudit()
    container = _FakeContainer(task_repo, candidate_repo, audit)

    result = await update_task_priority(
        container=container,
        actor_id=uuid4(),
        role="hr_recruiter",
        task_id=task.id,
        priority="high",
    )

    assert task.priority == "HIGH"
    assert candidate.priority == "HIGH"
    # Timer reopened and pushed into the future using the HIGH preset (24h triage).
    assert task.sla_frozen_at is None
    assert task.sla_outcome is None
    assert task.triage_deadline_at > datetime.utcnow()
    assert result["priority"] == "HIGH"
    assert result["sla_phase"] == "triage"
    assert result["sla_active"] is True
    assert result["sla_deadline_at"] is not None
    # The API must emit an explicit UTC offset so browsers don't reinterpret the
    # naive-UTC instant as local time (which shortened 24h -> 21h for UTC+3).
    assert result["sla_deadline_at"].endswith("+00:00")
    deadline = datetime.fromisoformat(result["sla_deadline_at"])
    remaining = deadline - datetime.now(UTC)
    assert timedelta(hours=23, minutes=59) < remaining <= timedelta(hours=24)
    assert [e["action"] for e in audit.events] == ["update_task_priority"]


async def test_priority_change_does_not_resurrect_resolved_timer() -> None:
    candidate_id, job_id = uuid4(), uuid4()
    task = ReviewTask(
        candidate_id=candidate_id,
        job_id=job_id,
        status=ReviewStatus.APPROVED,
        priority="LOW",
    )
    frozen_at = datetime.utcnow()
    task.sla_frozen_at = frozen_at
    task.sla_outcome = "completed_in_sla"
    candidate = Candidate(id=candidate_id, full_name="Alex", priority="LOW")

    container = _FakeContainer(
        _FakeReviewTaskRepo(task), _FakeCandidateRepo(candidate), _FakeAudit()
    )

    result = await update_task_priority(
        container=container,
        actor_id=uuid4(),
        role="hiring_manager",
        task_id=task.id,
        priority="medium",
    )

    assert task.priority == "MEDIUM"
    assert candidate.priority == "MEDIUM"
    assert task.sla_frozen_at == frozen_at
    assert task.sla_outcome == "completed_in_sla"
    assert result["sla_active"] is False
