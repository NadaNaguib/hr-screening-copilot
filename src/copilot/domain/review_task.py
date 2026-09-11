"""Review task domain model with state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from copilot.domain.errors import AuthorizationError, ValidationError


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
    audit_log: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def allowed_actions(self, role: str) -> list[ReviewAction]:
        return _ROLE_ACTIONS.get(role, {}).get(self.status, [])

    def is_action_allowed(self, role: str, action: ReviewAction) -> bool:
        return action in self.allowed_actions(role)

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
