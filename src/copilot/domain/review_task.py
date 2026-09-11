"""Review task domain model with state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from copilot.domain.errors import AuthorizationError, ValidationError


def utc_iso(dt: datetime | None) -> str | None:
    """Serialize a datetime as an explicit UTC ISO-8601 string.

    SLA deadlines are persisted as *naive UTC*. Emitting a bare
    ``"2026-09-11T12:00:00"`` makes browsers (``new Date(...)``) parse it as
    **local** time, which silently shortened a 24h window to 21h for a UTC+3
    client. Always attaching the UTC offset keeps the full duration intact.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


class ReviewStatus(str, Enum):
    PENDING_TRIAGE = "pending_triage"
    REJECTED_AT_TRIAGE = "rejected_at_triage"
    PENDING_MANAGER_REVIEW = "pending_manager_review"
    APPROVED = "approved"
    REJECTED_BY_MANAGER = "rejected_by_manager"
    EDITED_AND_APPROVED = "edited_and_approved"
    ESCALATED_TRIAGE = "escalated_triage"
    ESCALATED_MANAGER = "escalated_manager"


class ReviewAction(str, Enum):
    FORWARD_TO_MANAGER = "forward_to_manager"
    REJECT_AT_TRIAGE = "reject_at_triage"
    APPROVE = "approve"
    REJECT = "reject"
    EDIT_AND_APPROVE = "edit_and_approve"
    ADMIN_OVERRIDE = "admin_override"


_ROLE_ACTIONS: dict[str, dict[ReviewStatus, list[ReviewAction]]] = {
    "hr_recruiter": {
        ReviewStatus.PENDING_TRIAGE: [
            ReviewAction.FORWARD_TO_MANAGER,
            ReviewAction.REJECT_AT_TRIAGE,
        ],
    },
    "hiring_manager": {
        ReviewStatus.PENDING_MANAGER_REVIEW: [
            ReviewAction.APPROVE,
            ReviewAction.REJECT,
            ReviewAction.EDIT_AND_APPROVE,
        ],
    },
    "admin": {
        ReviewStatus.PENDING_TRIAGE: [ReviewAction.ADMIN_OVERRIDE],
        ReviewStatus.PENDING_MANAGER_REVIEW: [ReviewAction.ADMIN_OVERRIDE],
    },
}

_STATUS_TRANSITIONS: dict[ReviewAction, ReviewStatus] = {
    ReviewAction.FORWARD_TO_MANAGER: ReviewStatus.PENDING_MANAGER_REVIEW,
    ReviewAction.REJECT_AT_TRIAGE: ReviewStatus.REJECTED_AT_TRIAGE,
    ReviewAction.APPROVE: ReviewStatus.APPROVED,
    ReviewAction.REJECT: ReviewStatus.REJECTED_BY_MANAGER,
    ReviewAction.EDIT_AND_APPROVE: ReviewStatus.EDITED_AND_APPROVED,
}

# Statuses that terminate the workflow: once reached, the SLA timer freezes.
_TERMINAL_STATUSES = {
    ReviewStatus.APPROVED,
    ReviewStatus.REJECTED_BY_MANAGER,
    ReviewStatus.EDITED_AND_APPROVED,
    ReviewStatus.REJECTED_AT_TRIAGE,
}

# The two role-based SLA phases.
_TRIAGE_STATUSES = {ReviewStatus.PENDING_TRIAGE, ReviewStatus.ESCALATED_TRIAGE}
_DECISION_STATUSES = {ReviewStatus.PENDING_MANAGER_REVIEW, ReviewStatus.ESCALATED_MANAGER}

SLA_PHASE_TRIAGE = "triage"
SLA_PHASE_DECISION = "decision"
SLA_PHASE_RESOLVED = "resolved"

SLA_OUTCOME_COMPLETED = "completed_in_sla"
SLA_OUTCOME_BREACHED = "breached"

_REASON_ACTIONS = {
    ReviewAction.REJECT_AT_TRIAGE,
    ReviewAction.REJECT,
}

# Only a rejection must be justified. Approving or editing/approving a candidate
# never requires a comment, so the UI can save seamless edits.
REJECTION_COMMENT_REQUIRED = (
    "A comment explaining the decision is required before rejecting a candidate."
)


def _requires_reason(action: ReviewAction) -> bool:
    return action in _REASON_ACTIONS


@dataclass
class ReviewTask:
    id: UUID = field(default_factory=uuid4)
    candidate_id: UUID | None = None
    job_id: UUID | None = None
    status: ReviewStatus = ReviewStatus.PENDING_TRIAGE
    priority: str = "MEDIUM"
    triage_deadline_at: datetime | None = None
    decision_deadline_at: datetime | None = None
    triage_escalated_at: datetime | None = None
    decision_escalated_at: datetime | None = None
    triage_reason: str | None = None
    manager_comment: str | None = None
    admin_override_reason: str | None = None
    sla_frozen_at: datetime | None = None
    sla_outcome: str | None = None
    # Set when a hiring manager edits this candidate's interview probes so a
    # subsequent plain approval is recorded as ``edited_and_approved``.
    probes_edited: bool = False
    audit_log: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def allowed_actions(self, role: str) -> list[ReviewAction]:
        return _ROLE_ACTIONS.get(role, {}).get(self.status, [])

    def is_action_allowed(self, role: str, action: ReviewAction) -> bool:
        return action in self.allowed_actions(role)

    # -- SLA lifecycle helpers -------------------------------------------------

    def is_resolved(self) -> bool:
        """True once the task has reached a terminal status."""
        return self.status in _TERMINAL_STATUSES

    def sla_phase(self) -> str:
        """Return the active SLA phase (triage / decision / resolved)."""
        if self.status in _TRIAGE_STATUSES:
            return SLA_PHASE_TRIAGE
        if self.status in _DECISION_STATUSES:
            return SLA_PHASE_DECISION
        return SLA_PHASE_RESOLVED

    def active_sla_deadline(self) -> datetime | None:
        """Deadline governing the current phase (None once resolved)."""
        phase = self.sla_phase()
        if phase == SLA_PHASE_TRIAGE:
            return self.triage_deadline_at
        if phase == SLA_PHASE_DECISION:
            return self.decision_deadline_at
        return None

    def freeze_sla(self, deadline: datetime | None = None, now: datetime | None = None) -> None:
        """Freeze the SLA timer, recording whether it completed or breached."""
        if self.sla_frozen_at is not None:
            return
        now = now or datetime.utcnow()
        if deadline is None:
            deadline = self.triage_deadline_at or self.decision_deadline_at
        self.sla_frozen_at = now
        self.sla_outcome = (
            SLA_OUTCOME_BREACHED if deadline and now > deadline else SLA_OUTCOME_COMPLETED
        )

    def auto_forward_to_manager(self, now: datetime | None = None) -> bool:
        """Recruiter-SLA timeout: escalate the task to the Hiring Manager."""
        if self.status not in _TRIAGE_STATUSES:
            return False
        now = now or datetime.utcnow()
        self.status = ReviewStatus.PENDING_MANAGER_REVIEW
        self.triage_escalated_at = now
        self.audit_log.append(
            {
                "actor_role": "system",
                "actor_id": None,
                "action": "auto_forward_to_manager",
                "reason": "Recruiter triage SLA expired",
                "to_status": self.status.value,
                "timestamp": now.isoformat(),
            }
        )
        self.updated_at = now
        return True

    def auto_approve(self, now: datetime | None = None) -> bool:
        """Manager-SLA timeout: auto-approve the task and freeze the timer."""
        if self.status not in _DECISION_STATUSES:
            return False
        now = now or datetime.utcnow()
        deadline = self.decision_deadline_at
        self.status = ReviewStatus.APPROVED
        self.decision_escalated_at = now
        self.freeze_sla(deadline=deadline, now=now)
        self.audit_log.append(
            {
                "actor_role": "system",
                "actor_id": None,
                "action": "auto_approve",
                "reason": "Manager decision SLA expired",
                "to_status": self.status.value,
                "timestamp": now.isoformat(),
            }
        )
        self.updated_at = now
        return True

    def apply_action(
        self,
        role: str,
        action: ReviewAction,
        reason: str | None = None,
        actor_id: UUID | None = None,
    ) -> None:
        if not self.is_action_allowed(role, action):
            raise AuthorizationError(
                f"Action '{action.value}' not allowed for role '{role}' in status '{self.status.value}'"
            )
        # Capture the governing deadline BEFORE the status changes so the timer can
        # be frozen with the correct completed-vs-breached verdict.
        active_deadline = self.active_sla_deadline()
        # A manager who edited this candidate's interview probes is registering an
        # "edited & approved" decision — promote a plain approval to reflect that.
        if action == ReviewAction.APPROVE and self.probes_edited:
            action = ReviewAction.EDIT_AND_APPROVE
        if action == ReviewAction.ADMIN_OVERRIDE:
            if not reason:
                raise ValidationError("Admin override requires a mandatory reason")
            self.admin_override_reason = reason
            if self.status == ReviewStatus.PENDING_TRIAGE:
                self.status = ReviewStatus.PENDING_MANAGER_REVIEW
            elif self.status == ReviewStatus.PENDING_MANAGER_REVIEW:
                self.status = ReviewStatus.APPROVED
        else:
            if _requires_reason(action) and not reason:
                raise ValidationError(REJECTION_COMMENT_REQUIRED)
            self.status = _STATUS_TRANSITIONS[action]
        if action == ReviewAction.REJECT_AT_TRIAGE:
            self.triage_reason = reason
        if action in (ReviewAction.REJECT, ReviewAction.EDIT_AND_APPROVE):
            self.manager_comment = reason
        self.audit_log.append(
            {
                "actor_role": role,
                "actor_id": str(actor_id) if actor_id else None,
                "action": action.value,
                "reason": reason,
                "to_status": self.status.value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        # A definitive action resolves the task: stop the SLA countdown.
        if self.status in _TERMINAL_STATUSES:
            self.freeze_sla(deadline=active_deadline)
        self.updated_at = datetime.utcnow()

    def escalate_triage(self) -> None:
        if self.status == ReviewStatus.PENDING_TRIAGE:
            self.status = ReviewStatus.ESCALATED_TRIAGE
            self.triage_escalated_at = datetime.utcnow()
            self.audit_log.append(
                {
                    "action": "escalate_triage",
                    "to_status": self.status.value,
                    "timestamp": self.triage_escalated_at.isoformat(),
                }
            )

    def escalate_decision(self) -> None:
        if self.status == ReviewStatus.PENDING_MANAGER_REVIEW:
            self.status = ReviewStatus.ESCALATED_MANAGER
            self.decision_escalated_at = datetime.utcnow()
            self.audit_log.append(
                {
                    "action": "escalate_decision",
                    "to_status": self.status.value,
                    "timestamp": self.decision_escalated_at.isoformat(),
                }
            )
