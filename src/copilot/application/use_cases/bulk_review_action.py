"""Bulk (multi-select) review actions for the review queue.

WordPress-style bulk operations apply a single action to many review tasks at
once. The per-task rules are *not* duplicated here: each selected task is routed
through the very same use case the single-row buttons use
(``triage_candidate`` / ``decide_candidate``) so transitions, SLA handling and
audit logging stay identical. This module only adds:

* role/action routing (recruiter -> triage, manager -> decision),
* the "reject always needs a comment" guard applied *once* before any mutation,
* a per-task result summary so the UI can report partial success.
"""

from __future__ import annotations

from uuid import UUID

from copilot.application.use_cases.decide_candidate import decide_candidate
from copilot.application.use_cases.triage_candidate import triage_candidate
from copilot.domain.errors import AuthorizationError, NotFoundError, ValidationError
from copilot.infrastructure.di import Container

# Recruiter-tier bulk actions (handled by the /triage route).
_TRIAGE_ACTIONS = {"forward_to_manager", "reject_at_triage"}
# Manager-tier bulk actions (handled by the /decide route).
_DECIDE_ACTIONS = {"approve", "reject", "edit_and_approve"}
# Rejecting a candidate always requires an explanatory comment.
_REJECT_ACTIONS = {"reject", "reject_at_triage"}

REJECTION_COMMENT_REQUIRED = (
    "A comment explaining the decision is required before rejecting a candidate."
)


async def bulk_review_action(
    container: Container,
    actor_id: UUID,
    role: str,
    task_ids: list[UUID],
    action: str,
    reason: str | None = None,
    correlation_id: str = "",
) -> dict:
    """Apply ``action`` to every task in ``task_ids`` for the calling role."""
    if role == "admin":
        # Admin has read-only review-queue access; bulk mutations are forbidden.
        raise AuthorizationError("Admin cannot perform bulk review actions")
    if role not in {"hr_recruiter", "hiring_manager"}:
        raise AuthorizationError("Not authorized")

    if not task_ids:
        raise ValidationError("Select at least one candidate for a bulk action")

    if action in _TRIAGE_ACTIONS:
        if role != "hr_recruiter":
            raise AuthorizationError("Only hr_recruiter can perform triage actions")
    elif action in _DECIDE_ACTIONS:
        if role != "hiring_manager":
            raise AuthorizationError("Only hiring_manager can perform decision actions")
    else:
        raise ValidationError(f"Unsupported bulk action '{action}'")

    # Mandatory-comment rule (mirrors the single-row rule and the backend 400).
    comment = (reason or "").strip()
    if action in _REJECT_ACTIONS and not comment:
        raise ValidationError(REJECTION_COMMENT_REQUIRED)

    run = triage_candidate if action in _TRIAGE_ACTIONS else decide_candidate

    succeeded: list[str] = []
    failed: list[dict] = []
    for task_id in task_ids:
        try:
            await run(
                container=container,
                actor_id=actor_id,
                role=role,
                task_id=task_id,
                action=action,
                reason=comment or None,
                correlation_id=correlation_id,
            )
            succeeded.append(str(task_id))
        except (ValidationError, AuthorizationError, NotFoundError) as exc:
            # Domain-level rejection for this one task — keep processing the rest.
            failed.append({"task_id": str(task_id), "message": str(exc)})

    return {
        "action": action,
        "succeeded": succeeded,
        "failed": failed,
        "processed": len(succeeded),
    }
