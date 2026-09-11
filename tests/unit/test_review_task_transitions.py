"""Unit tests for review-task state machine transitions."""

from __future__ import annotations

from uuid import uuid4

import pytest

from copilot.domain.errors import AuthorizationError, ValidationError
from copilot.domain.review_task import ReviewAction, ReviewStatus, ReviewTask


def _task(status: ReviewStatus = ReviewStatus.PENDING_TRIAGE) -> ReviewTask:
    return ReviewTask(
        id=uuid4(),
        candidate_id=uuid4(),
        job_id=uuid4(),
        status=status,
    )


def test_recruiter_can_forward_from_pending_triage() -> None:
    task = _task(ReviewStatus.PENDING_TRIAGE)
    task.apply_action("hr_recruiter", ReviewAction.FORWARD_TO_MANAGER, reason="Strong fit")
    assert task.status == ReviewStatus.PENDING_MANAGER_REVIEW


def test_recruiter_can_reject_at_triage() -> None:
    task = _task(ReviewStatus.PENDING_TRIAGE)
    task.apply_action("hr_recruiter", ReviewAction.REJECT_AT_TRIAGE, reason="Missing skills")
    assert task.status == ReviewStatus.REJECTED_AT_TRIAGE


def test_hiring_manager_cannot_act_on_pending_triage() -> None:
    task = _task(ReviewStatus.PENDING_TRIAGE)
    with pytest.raises(AuthorizationError):
        task.apply_action("hiring_manager", ReviewAction.APPROVE, reason="Looks good")


def test_manager_can_approve_pending_manager_review() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.apply_action("hiring_manager", ReviewAction.APPROVE, reason="Approved")
    assert task.status == ReviewStatus.APPROVED


def test_manager_can_reject_pending_manager_review() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.apply_action("hiring_manager", ReviewAction.REJECT, reason="Not a fit")
    assert task.status == ReviewStatus.REJECTED_BY_MANAGER


def test_manager_can_edit_and_approve() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.apply_action("hiring_manager", ReviewAction.EDIT_AND_APPROVE, reason="Approved with edits")
    assert task.status == ReviewStatus.EDITED_AND_APPROVED


def test_recruiter_cannot_decide_at_manager_stage() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    with pytest.raises(AuthorizationError):
        task.apply_action("hr_recruiter", ReviewAction.APPROVE, reason="I approve")


def test_admin_override_requires_reason() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    with pytest.raises(ValidationError):
        task.apply_action("admin", ReviewAction.ADMIN_OVERRIDE, reason="")


def test_admin_override_with_reason_succeeds() -> None:
    task = _task(ReviewStatus.PENDING_TRIAGE)
    task.apply_action("admin", ReviewAction.ADMIN_OVERRIDE, reason="Break-glass override")
    assert task.status == ReviewStatus.PENDING_MANAGER_REVIEW
