"""Unit tests for review-task state machine transitions."""

from __future__ import annotations

from datetime import datetime, timedelta
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


def test_reject_requires_a_comment() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    with pytest.raises(ValidationError, match="comment explaining the decision is required"):
        task.apply_action("hiring_manager", ReviewAction.REJECT, reason="")


def test_approve_does_not_require_a_comment() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.apply_action("hiring_manager", ReviewAction.APPROVE)
    assert task.status == ReviewStatus.APPROVED


def test_edit_and_approve_does_not_require_a_comment() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.apply_action("hiring_manager", ReviewAction.EDIT_AND_APPROVE)
    assert task.status == ReviewStatus.EDITED_AND_APPROVED


def test_approve_freezes_sla_as_completed() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.decision_deadline_at = datetime.utcnow() + timedelta(hours=1)
    task.apply_action("hiring_manager", ReviewAction.APPROVE)
    assert task.sla_frozen_at is not None
    assert task.sla_outcome == "completed_in_sla"
    assert task.active_sla_deadline() is None


def test_reject_after_deadline_records_breach() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.decision_deadline_at = datetime.utcnow() - timedelta(hours=1)
    task.apply_action("hiring_manager", ReviewAction.REJECT, reason="Not a fit")
    assert task.sla_outcome == "breached"
    assert task.sla_frozen_at is not None


def test_auto_forward_to_manager_on_triage_timeout() -> None:
    task = _task(ReviewStatus.PENDING_TRIAGE)
    assert task.auto_forward_to_manager() is True
    assert task.status == ReviewStatus.PENDING_MANAGER_REVIEW
    assert task.triage_escalated_at is not None
    # The timer survives escalation so the manager window keeps counting.
    assert task.sla_frozen_at is None


def test_auto_approve_on_decision_timeout_freezes_sla() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.decision_deadline_at = datetime.utcnow() - timedelta(hours=1)
    assert task.auto_approve() is True
    assert task.status == ReviewStatus.APPROVED
    assert task.sla_outcome == "breached"
    assert task.sla_frozen_at is not None


def test_auto_forward_ignored_outside_triage_phase() -> None:
    task = _task(ReviewStatus.APPROVED)
    assert task.auto_forward_to_manager() is False
    assert task.status == ReviewStatus.APPROVED


def test_triage_phase_uses_triage_deadline() -> None:
    task = _task(ReviewStatus.PENDING_TRIAGE)
    task.triage_deadline_at = datetime.utcnow() + timedelta(hours=2)
    task.decision_deadline_at = datetime.utcnow() + timedelta(hours=50)
    assert task.sla_phase() == "triage"
    assert task.active_sla_deadline() == task.triage_deadline_at


def test_decision_phase_uses_decision_deadline() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.triage_deadline_at = datetime.utcnow() - timedelta(hours=2)
    task.decision_deadline_at = datetime.utcnow() + timedelta(hours=50)
    assert task.sla_phase() == "decision"
    assert task.active_sla_deadline() == task.decision_deadline_at


def test_approve_after_probe_edits_becomes_edited_and_approved() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    task.probes_edited = True
    task.apply_action("hiring_manager", ReviewAction.APPROVE)
    assert task.status == ReviewStatus.EDITED_AND_APPROVED


def test_approve_without_probe_edits_stays_approved() -> None:
    task = _task(ReviewStatus.PENDING_MANAGER_REVIEW)
    assert task.probes_edited is False
    task.apply_action("hiring_manager", ReviewAction.APPROVE)
    assert task.status == ReviewStatus.APPROVED
