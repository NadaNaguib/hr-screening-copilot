"""Unit tests for the WordPress-style bulk review actions use case."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from copilot.application.use_cases.bulk_review_action import (
    REJECTION_COMMENT_REQUIRED,
    bulk_review_action,
)
from copilot.domain.errors import AuthorizationError, ValidationError
from copilot.domain.review_task import ReviewStatus, ReviewTask


class _FakeReviewTaskRepo:
    def __init__(self, tasks: dict[UUID, ReviewTask]) -> None:
        self._tasks = tasks
        self.updated: list[ReviewTask] = []

    async def get_task(self, task_id: UUID) -> ReviewTask | None:
        return self._tasks.get(task_id)

    async def update_task(self, task: ReviewTask) -> ReviewTask:
        self.updated.append(task)
        return task

    async def get_sla_rule_for_job(self, job_id):
        return None


class _FakeDocumentRepo:
    async def get_job(self, job_id):
        return None


class _FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def log(self, **kwargs) -> None:
        self.events.append(kwargs)


class _FakeContainer:
    def __init__(self, repo: _FakeReviewTaskRepo) -> None:
        self.review_task_repository = repo
        self.document_repository = _FakeDocumentRepo()
        self.audit = _FakeAudit()


def _triage_task() -> ReviewTask:
    return ReviewTask(candidate_id=uuid4(), status=ReviewStatus.PENDING_TRIAGE, priority="HIGH")


def _manager_task() -> ReviewTask:
    return ReviewTask(
        candidate_id=uuid4(),
        status=ReviewStatus.PENDING_MANAGER_REVIEW,
        priority="HIGH",
    )


async def test_admin_cannot_run_bulk_actions() -> None:
    repo = _FakeReviewTaskRepo({})
    with pytest.raises(AuthorizationError):
        await bulk_review_action(
            container=_FakeContainer(repo),
            actor_id=uuid4(),
            role="admin",
            task_ids=[uuid4()],
            action="forward_to_manager",
        )


async def test_bulk_reject_requires_comment() -> None:
    task = _manager_task()
    repo = _FakeReviewTaskRepo({task.id: task})
    with pytest.raises(ValidationError, match=REJECTION_COMMENT_REQUIRED):
        await bulk_review_action(
            container=_FakeContainer(repo),
            actor_id=uuid4(),
            role="hiring_manager",
            task_ids=[task.id],
            action="reject",
            reason="   ",
        )
    # Nothing is mutated when the mandatory comment is missing.
    assert repo.updated == []


async def test_recruiter_bulk_forward_applies_to_all_selected() -> None:
    t1, t2 = _triage_task(), _triage_task()
    repo = _FakeReviewTaskRepo({t1.id: t1, t2.id: t2})
    result = await bulk_review_action(
        container=_FakeContainer(repo),
        actor_id=uuid4(),
        role="hr_recruiter",
        task_ids=[t1.id, t2.id],
        action="forward_to_manager",
    )
    assert result["processed"] == 2
    assert result["failed"] == []
    assert t1.status == ReviewStatus.PENDING_MANAGER_REVIEW
    assert t2.status == ReviewStatus.PENDING_MANAGER_REVIEW


async def test_recruiter_cannot_run_manager_bulk_action() -> None:
    repo = _FakeReviewTaskRepo({})
    with pytest.raises(AuthorizationError):
        await bulk_review_action(
            container=_FakeContainer(repo),
            actor_id=uuid4(),
            role="hr_recruiter",
            task_ids=[uuid4()],
            action="approve",
        )


async def test_bulk_reports_partial_failure_for_missing_task() -> None:
    task = _triage_task()
    repo = _FakeReviewTaskRepo({task.id: task})
    missing = uuid4()
    result = await bulk_review_action(
        container=_FakeContainer(repo),
        actor_id=uuid4(),
        role="hr_recruiter",
        task_ids=[task.id, missing],
        action="forward_to_manager",
    )
    assert result["processed"] == 1
    assert result["succeeded"] == [str(task.id)]
    assert len(result["failed"]) == 1
    assert result["failed"][0]["task_id"] == str(missing)
