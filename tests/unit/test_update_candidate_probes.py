"""Unit tests for probe edits tracking (manager -> edited_and_approved)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from copilot.application.use_cases.update_candidate_probes import (
    normalize_probes,
    update_candidate_probes,
)
from copilot.domain.candidate import Candidate
from copilot.domain.review_task import ReviewStatus, ReviewTask


class _FakeCandidateRepo:
    def __init__(self, candidate: Candidate) -> None:
        self._candidate = candidate
        self.updated: list[Candidate] = []

    async def get_candidate(self, candidate_id):
        return self._candidate

    async def update_candidate(self, candidate: Candidate) -> Candidate:
        self.updated.append(candidate)
        return candidate


class _FakeReviewTaskRepo:
    def __init__(self, task: ReviewTask | None) -> None:
        self._task = task
        self.updated: list[ReviewTask] = []

    async def get_task_by_candidate(self, candidate_id):
        return self._task

    async def update_task(self, task: ReviewTask) -> ReviewTask:
        self.updated.append(task)
        return task


class _FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def log(self, **kwargs) -> None:
        self.events.append(kwargs)


def _container(candidate: Candidate, task: ReviewTask | None) -> SimpleNamespace:
    return SimpleNamespace(
        candidate_repository=_FakeCandidateRepo(candidate),
        review_task_repository=_FakeReviewTaskRepo(task),
        audit=_FakeAudit(),
    )


def _candidate(probes: list[dict] | None = None) -> Candidate:
    return Candidate(id=uuid4(), full_name="Ada Lovelace", interview_probes=probes or [])


def test_normalize_probes_drops_empty_questions() -> None:
    cleaned = normalize_probes(
        [
            {"category": "technical", "question": "  "},
            {"category": "gap", "question": "Explain the gap"},
        ]
    )
    assert cleaned == [{"category": "gap", "question": "Explain the gap"}]


async def test_manager_edit_flags_review_task() -> None:
    candidate = _candidate([{"category": "technical", "question": "Original?"}])
    task = ReviewTask(
        candidate_id=candidate.id, status=ReviewStatus.PENDING_MANAGER_REVIEW, priority="HIGH"
    )
    container = _container(candidate, task)

    result = await update_candidate_probes(
        container=container,
        candidate_id=candidate.id,
        role="hiring_manager",
        probes=[{"category": "technical", "question": "Edited question?"}],
    )

    assert result["manager_modified"] is True
    assert task.probes_edited is True
    assert container.review_task_repository.updated == [task]


async def test_recruiter_edit_does_not_flag_task() -> None:
    candidate = _candidate([{"category": "technical", "question": "Original?"}])
    task = ReviewTask(candidate_id=candidate.id, status=ReviewStatus.PENDING_TRIAGE)
    container = _container(candidate, task)

    result = await update_candidate_probes(
        container=container,
        candidate_id=candidate.id,
        role="hr_recruiter",
        probes=[{"category": "technical", "question": "Edited question?"}],
    )

    assert result["manager_modified"] is False
    assert task.probes_edited is False
    assert container.review_task_repository.updated == []


async def test_manager_saving_unchanged_probes_does_not_flag() -> None:
    probes = [{"category": "technical", "question": "Same?"}]
    candidate = _candidate(probes)
    task = ReviewTask(candidate_id=candidate.id, status=ReviewStatus.PENDING_MANAGER_REVIEW)
    container = _container(candidate, task)

    result = await update_candidate_probes(
        container=container,
        candidate_id=candidate.id,
        role="hiring_manager",
        probes=probes,
    )

    assert result["manager_modified"] is False
    assert task.probes_edited is False


async def test_manager_edit_does_not_flag_resolved_task() -> None:
    candidate = _candidate([{"category": "technical", "question": "Original?"}])
    task = ReviewTask(candidate_id=candidate.id, status=ReviewStatus.APPROVED)
    container = _container(candidate, task)

    result = await update_candidate_probes(
        container=container,
        candidate_id=candidate.id,
        role="hiring_manager",
        probes=[{"category": "technical", "question": "Late edit?"}],
    )

    assert result["manager_modified"] is False
    assert task.probes_edited is False
